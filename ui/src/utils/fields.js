import { isNumeric } from "@/utils/utils.js"


const DOT = "."
const DOUBLE_QUOTE = '"'
const SINGLE_QUOTE = "'"
const MODIFIER_OPERATOR = "|"
const MODIFIER_ARGUMENT_DELIMITER = ","
const FIELDS_DELIMITER = ","
const SPACE = " "
const ALIAS_DELIMITER = " "
const COLON = ":"
const SLASH = "/"
const BACKSLASH = "\\"
const BRACKET_OPEN = "("
const BRACKET_CLOSE = ")"
const UNDERSCORE = "_"
const NEWLINE = "\n"
const VALID_ALIAS_OPERATOR = "as"

const CHARS = {
    DOT,
    DOUBLE_QUOTE,
    SINGLE_QUOTE,
    MODIFIER_OPERATOR,
    MODIFIER_ARGUMENT_DELIMITER,
    FIELDS_DELIMITER,
    SPACE,
    ALIAS_DELIMITER,
    COLON,
    SLASH,
    BACKSLASH,
    BRACKET_OPEN,
    BRACKET_CLOSE,
    UNDERSCORE,
    NEWLINE,
    VALID_ALIAS_OPERATOR,
}

class ParserError extends Error {
    constructor(message, errno) {
        super(message)
        this.errno = errno
    }

    toString() {
        return this.message
    }

    toRepresentation() {
        return this.toString()
    }
}

const escapeSequences = Object.freeze({
    'b': '\b',
    'f': '\f',
    'n': '\n',
    'r': '\r',
    't': '\t',
    'v': '\v',
    '\\': '\\',
})

const CharType = Object.freeze({
    FIELD: "field",
    ARGUMENT: "argument",
    OPERATOR: "operator",
    MODIFIER: "modifier",
    DELIMITER: "delimiter",
    ALIAS: "alias",
    ERROR: "error",
    NUMBER: "number",
    STRING: "string",
})

const tokenTypes = [
    CharType.FIELD,
    CharType.OPERATOR,
    CharType.ARGUMENT,
    CharType.MODIFIER,
    CharType.ALIAS,
    CharType.ERROR,
    CharType.NUMBER,
    CharType.STRING,
]

const State = Object.freeze({
    ERROR: "Error",
    NAME: "Name",
    EXPECT_NAME: "ExpectName",
    EXPECT_ALIAS: "ExpectAlias",
    EXPECT_ALIAS_OPERATOR: "ExpectAliasOperator",
    EXPECT_ALIAS_DELIMITER: "ExpectAliasDelimiter",
    EXPECT_MODIFIER: "ExpectModifier",
    MODIFIER: "Modifier",
    MODIFIER_COMPLETE: "ModifierComplete",
    MODIFIER_OPERATOR: "ModifierOperator",
    MODIFIER_ARGUMENT: "ModifierArgument",
    MODIFIER_ARGUMENT_DOUBLE_QUOTED: "ModifierArgumentDoubleQuoted",
    MODIFIER_ARGUMENT_SINGLE_QUOTED: "ModifierArgumentSingleQuoted",
    EXPECT_MODIFIER_ARGUMENT: "ExpectModifierArgument",
    EXPECT_MODIFIER_ARGUMENT_DELIMITER: "ExpectModifierArgumentDelimiter",
    SINGLE_QUOTED_ARGUMENT: "SingleQuotedArgument",
    DOUBLE_QUOTED_ARGUMENT: "DoubleQuotedArgument",
    MODIFIER_ARGUMENT_DELIMITER: "ArgumentDelimiter"
})

class Token {
    constructor(char, charType) {
        this.start = char.pos
        this.length = char.value.length
        this.type = charType
        this.value = char.value
        this.line = char.line
        this.linePos = char.linePos
    }
    addChar(char) {
        this.value += char.value
        this.length += char.value.length
    }
}

class Char {
    constructor(value, pos, line, linePos) {
        this.value = value
        this.pos = pos
        this.line = line
        this.linePos = linePos
    }
    isFieldValue() {
        return (
            /^[a-zA-Z0-9]$/.test(this.value) ||
            this.value === UNDERSCORE ||
            this.value === DOT ||
            this.value === COLON ||
            this.value === SLASH
        )
    }
    isModifierArgumentValue() {
        return (
            this.value !== MODIFIER_ARGUMENT_DELIMITER &&
            this.value !== BRACKET_OPEN &&
            this.value !== BRACKET_CLOSE
        )
    }

    isModifierDoubleQuotedArgumentValue() {
        return !this.isDoubleQuote()
    }

    isModifierSingleQuotedArgumentValue() {
        return !this.isSingleQuote()
    }
    isModifierValue() {
        return /^[a-zA-Z0-9]$/.test(this.value) || this.value === UNDERSCORE
    }

    isAliasChar() {
        return ["A", "a", "S", "s"].includes(this.value)
    }

    isBracketOpen() {
        return this.value === BRACKET_OPEN
    }

    isBracketClose() {
        return this.value === BRACKET_CLOSE
    }

    isDoubleQuote() {
        return this.value === DOUBLE_QUOTE
    }

    isSingleQuote() {
        return this.value === SINGLE_QUOTE
    }

    isModifierOperator() {
        return this.value === MODIFIER_OPERATOR
    }

    isModifierArgumentDelimiter() {
        return this.value === MODIFIER_ARGUMENT_DELIMITER
    }

    isFieldsDelimiter() {
        return this.value === FIELDS_DELIMITER
    }

    isAliasDelimiter() {
        return this.value === ALIAS_DELIMITER
    }

    isSpace() {
        return this.value === SPACE
    }

    isBackslash() {
        return this.value === BACKSLASH
    }

    isNewline() {
        return this.value === NEWLINE
    }
}

class Parser {
    constructor() {
        this.line = 0
        this.linePos = 0
        this.char = null
        this.state = State.EXPECT_NAME
        this.errorText = ""
        this.errno = 0
        this.field = ""
        this.alias = ""
        this.aliasOperator = ""
        this.modifier = ""
        this.modifierArgument = ""
        this.modifierArgumentType = "auto"
        this.modifiers = []
        this.modifierArguments = []
        this.fields = []
        this.typedChars = []
    }
    setText(text) {
        this.text = text
    }

    storeField() {
        this.fields.push({
            name: this.field,
            modifiers: this.modifiers,
            alias: this.alias
        })
        this.resetData()
    }
    storeModifier() {
        this.modifiers.push({
            name: this.modifier,
            arguments: this.modifierArguments
        })
        this.resetModifier()
    }
    storeArgument() {
        let value = this.modifierArgument
        
        if (this.modifierArgumentType === "auto") {
            try {
                value = parseInt(value)
            } catch (e) {
                try {
                    value = parseFloat(value)
                } catch (e) {
                    
                    // value remains as it is
                }
            }
        }
        this.modifierArguments.push(value)
        this.resetModifierArgument()
    }
    storeTypedChar(charType) {
        this.typedChars.push([this.char, charType])
    }

    setChar(char) {
        this.char = char
    }

    setState(state) {
        this.state = state
    }

    resetModifier() {
        this.modifier = ""
        this.modifierArguments = []
        this.modifierArgument = ""
    }
    resetField() {
        this.field = ""
    }

    resetAliasOperator() {
        this.aliasOperator = ""
    }

    resetAlias() {
        this.alias = ""
    }

    resetModifiers() {
        this.modifiers = []
    }

    resetModifierArgument() {
        this.modifierArgument = ""
        this.modifierArgumentType = "auto"
    }
    resetData() {
        this.resetField()
        this.resetAlias()
        this.resetModifier()
        this.resetModifiers()
        this.resetAliasOperator()
    }

    setErrorState(errorText, errno) {
        this.state = State.ERROR
        this.errorText = errorText
        this.errno = errno
        if (this.char) {
            this.errorText += ` [char ${this.char.value} at pos ${this.char.pos}], errno=${errno}`
        }
    }
    extendField() {
        this.field += this.char.value
    }

    extendModifier() {
        this.modifier += this.char.value
    }

    extendModifierArgument() {
        this.modifierArgument += this.char.value
    }

    extendAlias() {
        this.alias += this.char.value
    }

    extendAliasOperator() {
        this.aliasOperator += this.char.value
    }
    generateMonacoTokens() {
        const tokens = []
        let token = null
        for (const [char, charType] of this.typedChars) {
            if (token == null) {
                token = new Token(char, charType)
            } else {
                if (token.type == charType) {
                    token.addChar(char)
                } else {
                    tokens.push(token)
                    token = new Token(char, charType)
                }
            }
        }
        if (token !== null) {
            tokens.push(token)
        }
        for (const token of tokens) {
            if (token.type === CharType.ARGUMENT) {
                if (isNumeric(token.value)) {
                    token.type = CharType.NUMBER
                } else {
                    token.type = CharType.STRING
                }
            }
        }
        const data = []
        const tokenModifier = 0
        let prevToken = null
        for (const [index, token] of tokens.entries()) {
            let deltaLine = 0
            let deltaStart = token.linePos
            let tokenLength = token.length
            let typeIndex = tokenTypes.indexOf(token.type)

            if (prevToken != null) {
                deltaLine = token.line - prevToken.line
                deltaStart = deltaLine === 0 ? token.start - prevToken.start : token.linePos
                prevToken = token
            } else {
                prevToken = token
            }

            data.push(deltaLine, deltaStart, tokenLength, typeIndex, tokenModifier)
        }
        return data
    }
    getFields(source, raiseError) {
        const data = []
        this.fields.forEach(field => {
            const sourceFieldName = field.name.split(":")[0]
            if (!source.fields[sourceFieldName]) {
                if (raiseError) {
                    throw new ParserError(
                        `Source has no '${sourceFieldName}' field`, 100
                    )
                } else {
                    return
                }
            }
            const sourceField = source.fields[sourceFieldName]
            const displayName = field.alias || sourceField.display_name || field.name

            data.push({
                name: field.name,
                root_name: sourceFieldName,
                type: sourceField.type,
                display_name: displayName,
                modifiers: field.modifiers,
            })
        })
        return data
    }
    getFieldsNames(source, raiseError) {
        const names = []
        for (const field of this.getFields(source, raiseError)) {
            names.push(field.root_name)
        }
        return names
    }
    parse(text, raiseError) {
        this.setText(text)
        let i = 0
        while (i < text.length) {
            if (this.state === State.ERROR) {
                break
            }
            this.setChar(new Char(text[i], i, this.line, this.linePos))
            if (this.char.isBackslash()) {
                const nextChar = text[i + 1]
                if (nextChar && escapeSequences.hasOwnProperty(nextChar)) {
                    this.setChar(new Char(escapeSequences[nextChar], i, this.line, this.linePos))
                    i++
                }
            }
            
            if (this.char.isNewline()) {
                this.line += 1
                this.linePos = 0
                i++
                continue
            }
            if (this.state === State.EXPECT_NAME) {
                this.inStateExpectField()
            } else if (this.state === State.NAME) {
                this.inStateField()
            } else if (this.state === State.EXPECT_ALIAS) {
                this.inStateExpectAlias()
            } else if (this.state === State.EXPECT_ALIAS_OPERATOR) {
                this.inStateExpectAliasOperator()
            } else if (this.state === State.EXPECT_ALIAS_DELIMITER) {
                this.inStateExpectAliasDelimiter()
            } else if (this.state === State.EXPECT_MODIFIER) {
                this.inStateExpectModifier()
            } else if (this.state === State.EXPECT_MODIFIER_ARGUMENT) {
                this.inStateExpectModifierArgument()
            } else if (this.state === State.MODIFIER) {
                this.inStateModifier()
            } else if (this.state === State.MODIFIER_ARGUMENT) {
                this.inStateModifierArgument()
            } else if (this.state === State.MODIFIER_COMPLETE) {
                this.inStateModifierComplete()
            } else if (this.state === State.MODIFIER_ARGUMENT_DOUBLE_QUOTED) {
                this.inStateModifierArgumentDoubleQuoted()
            } else if (this.state === State.MODIFIER_ARGUMENT_SINGLE_QUOTED) {
                this.inStateModifierArgumentSingleQuoted()
            } else if (this.state === State.EXPECT_MODIFIER_ARGUMENT_DELIMITER) {
                this.inStateExpectModifierArgumentDelimiter()
            } else {
                this.setErrorState(`unknown state: ${this.state}`, 1)
            }

            this.linePos += 1
            i++
        }

        if (this.state === State.ERROR) {
            if (raiseError) {
                throw new ParserError({
                    message: this.errorText,
                    errno: this.errno
                })
            } else {
                return
            }
        }

        this.inStateLastChar()

        if (this.state === State.ERROR) {
            if (raiseError) {
                throw new ParserError({
                    message: this.errorText,
                    errno: this.errno
                })
            } else {
                return
            }
        }
    }
    inStateLastChar() {
        if (this.state === State.NAME) {
            this.storeField()
        } else if (this.state === State.EXPECT_ALIAS) {
            if (this.alias) {
                this.storeField()
            } else {
                this.setErrorState(`unexpected end of alias. Expected alias value`, 13)
            }
        } else if (this.state === State.EXPECT_ALIAS_OPERATOR || this.state === State.EXPECT_ALIAS_DELIMITER) {
            this.setErrorState(`unexpected end of alias. Expected alias value`, 14)
        } else if (this.state === State.MODIFIER) {
            if (this.modifier) {
                this.storeModifier()
            }
            if (this.field) {
                this.storeField()
            }
        } else if (this.state === State.MODIFIER_COMPLETE) {
            this.storeModifier()
            this.storeField()
        } else if (this.state === State.MODIFIER_ARGUMENT_DOUBLE_QUOTED || this.state === State.MODIFIER_ARGUMENT_SINGLE_QUOTED) {
            this.setErrorState(`unexpected end of quoted argument value`, 12)
        } else if (this.state === State.EXPECT_MODIFIER_ARGUMENT_DELIMITER) {
            this.setErrorState(`unexpected end of arguments list`, 15)
        }
    }
    inStateExpectField() {
        if (this.char.isSpace()) {
            return
        } else if (this.char.isFieldValue()) {
            this.extendField()
            this.storeTypedChar(CharType.FIELD)
            this.setState(State.NAME)
        } else {
            this.storeTypedChar(CharType.ERROR)
            this.setErrorState(`invalid character`, 2)
            return
        }
    }
    inStateField() {
        if (this.char.isSpace()) {
            this.setState(State.EXPECT_ALIAS_OPERATOR)
        } else if (this.char.isFieldValue()) {
            this.extendField()
            this.storeTypedChar(CharType.FIELD)
        } else if (this.char.isFieldsDelimiter()) {
            this.setState(State.EXPECT_NAME)
            this.storeField()
            this.storeTypedChar(CharType.OPERATOR)
        } else if (this.char.isModifierOperator()) {
            this.storeTypedChar(CharType.OPERATOR)
            this.setState(State.EXPECT_MODIFIER)
        } else {
            this.storeTypedChar(CharType.ERROR)
            this.setErrorState(`invalid character`, 6)
        }
    }
    inStateExpectModifier() {
        if (this.char.isModifierValue()) {
            this.extendModifier()
            this.storeTypedChar(CharType.MODIFIER)
            this.setState(State.MODIFIER)
        } else {
            this.storeTypedChar(CharType.ERROR)
            this.setErrorState(`invalid character, expected modifier`, 7)
        }
    }
    inStateModifier() {
        if (this.char.isModifierValue()) {
            this.extendModifier()
            this.storeTypedChar(CharType.MODIFIER)
        } else if (this.char.isFieldsDelimiter()) {
            this.storeModifier()
            this.storeField()
            this.storeTypedChar(CharType.OPERATOR)
            this.setState(State.EXPECT_NAME)
        } else if (this.char.isModifierOperator()) {
            this.storeModifier()
            this.storeTypedChar(CharType.OPERATOR)
            this.setState(State.EXPECT_MODIFIER)
        } else if (this.char.isSpace()) {
            this.storeModifier()
            this.setState(State.EXPECT_ALIAS_OPERATOR)
        } else if (this.char.isBracketOpen()) {
            this.storeTypedChar(CharType.OPERATOR)
            this.setState(State.EXPECT_MODIFIER_ARGUMENT)
        } else if (this.char.isBracketClose()) {
            this.storeArgument()
            this.storeModifier()
            this.storeTypedChar(CharType.ERROR)
            this.setErrorState(`invalid character, expected modifier`, 17)
        } else {
            this.storeTypedChar(CharType.ERROR)
            this.setErrorState(`invalid character, expected modifier`, 19)
        }
    }
    inStateExpectModifierArgument() {
        if (this.char.isSpace()) {
            return
        }
        if (this.char.isDoubleQuote()) {
            this.modifierArgumentType = "str"
            this.setState(State.MODIFIER_ARGUMENT_DOUBLE_QUOTED)
            this.storeTypedChar(CharType.ARGUMENT)
        } else if (this.char.isSingleQuote()) {
            this.modifierArgumentType = "str"
            this.setState(State.MODIFIER_ARGUMENT_SINGLE_QUOTED)
            this.storeTypedChar(CharType.ARGUMENT)
        } else if (this.char.isModifierArgumentValue()) {
            this.extendModifierArgument()
            this.setState(State.MODIFIER_ARGUMENT)
            this.storeTypedChar(CharType.ARGUMENT)
        }
    }
    inStateModifierArgument() {
        if (this.char.isModifierArgumentDelimiter()) {
            this.storeArgument()
            this.setState(State.EXPECT_MODIFIER_ARGUMENT)
            this.storeTypedChar(CharType.OPERATOR)
        } else if (this.char.isModifierArgumentValue()) {
            this.extendModifierArgument()
            this.storeTypedChar(CharType.ARGUMENT)
        } else if (this.char.isBracketClose()) {
            this.storeArgument()
            this.storeTypedChar(CharType.OPERATOR)
            this.setState(State.MODIFIER_COMPLETE)
        }
    }
    inStateExpectModifierArgumentDelimiter() {
        if (this.char.isModifierArgumentDelimiter()) {
            this.setState(State.EXPECT_MODIFIER_ARGUMENT)
            this.storeTypedChar(CharType.OPERATOR)
        } else if (this.char.isBracketClose()) {
            this.storeTypedChar(CharType.OPERATOR)
            this.setState(State.MODIFIER_COMPLETE)
        } else {
            this.storeTypedChar(CharType.ERROR)
            this.setErrorState(
                `invalid character. Expected bracket close or modifier argument delimiter`,
                9
            )
            return
        }
    }
    inStateModifierArgumentDoubleQuoted() {
        this.storeTypedChar(CharType.ARGUMENT)
        if (this.char.isBackslash()) {
            const nextPos = this.char.pos + 1
            let nextChar
            try {
                nextChar = this.text[nextPos]
            } catch (e) {
                this.extendModifierArgument()
            }
            if (nextChar !== DOUBLE_QUOTE) {
                this.extendModifierArgument()
            }
        } else if (this.char.isModifierDoubleQuotedArgumentValue()) {
            this.extendModifierArgument()
        } else if (this.char.isDoubleQuote()) {
            const prevPos = this.char.pos - 1
            if (this.text[prevPos] === BACKSLASH) {
                this.extendModifierArgument()
            } else {
                this.storeArgument()
                this.setState(State.EXPECT_MODIFIER_ARGUMENT_DELIMITER)
            }
        } else {
            this.storeTypedChar(CharType.ERROR)
            this.setErrorState(`invalid character`, 10)
            return
        }
    }
    inStateModifierArgumentSingleQuoted() {
        this.storeTypedChar(CharType.ARGUMENT)
        if (this.char.isBackslash()) {
            const nextPos = this.char.pos + 1
            let nextChar = this.text[nextPos]
            try {
                nextChar = this.text[nextPos]
            } catch (e) {
                this.extendModifierArgument()
            }
            if (nextChar !== SINGLE_QUOTE) {
                this.extendModifierArgument()
            }
        } else if (this.char.isModifierSingleQuotedArgumentValue()) {
            this.extendModifierArgument()
        } else if (this.char.isSingleQuote()) {
            const prevPos = this.char.pos - 1
            if (this.text[prevPos] === BACKSLASH) {
                this.extendModifierArgument()
            } else {
                this.storeArgument()
                this.setState(State.EXPECT_MODIFIER_ARGUMENT_DELIMITER)
            }
        } else {
            this.storeTypedChar(CharType.ERROR)
            this.setErrorState(`invalid character`, 10)
            return
        }
    }
    inStateModifierComplete() {
        if (this.char.isSpace()) {
            this.storeModifier()
            this.setState(State.EXPECT_ALIAS_OPERATOR)
        } else if (this.char.isFieldsDelimiter()) {
            this.storeModifier()
            this.storeField()
            this.setState(State.EXPECT_NAME)
            this.storeTypedChar(CharType.OPERATOR)
        } else if (this.char.isModifierOperator()) {
            this.storeModifier()
            this.storeTypedChar(CharType.OPERATOR)
            this.setState(State.EXPECT_MODIFIER)
        } else {
            this.storeTypedChar(CharType.ERROR)
            this.setErrorState(`invalid character`, 8)
        }
    }
    inStateExpectAliasOperator() {
        if (this.char.isSpace()) {
            return
        } else if (this.char.isAliasChar()) {
            this.extendAliasOperator()
            this.storeTypedChar(CharType.OPERATOR)
            if (this.aliasOperator.length < 2) {
                return
            }
            if (this.aliasOperator.length === 2) {
                if (this.aliasOperator.toLowerCase() !== VALID_ALIAS_OPERATOR) {
                    this.setErrorState("invalid character", 3)
                } else {
                    this.setState(State.EXPECT_ALIAS_DELIMITER)
                    this.resetAliasOperator()
                }
            } else {
                return
            }
        } else {
            this.storeTypedChar(CharType.ERROR)
            this.setErrorState("invalid character, expected alias operator", 4)
        }
    }
    inStateExpectAlias() {
        if (this.char.isSpace()) {
            return
        } else if (this.char.isFieldValue()) {
            this.extendAlias()
            this.storeTypedChar(CharType.ALIAS)
        } else if (this.char.isFieldsDelimiter()) {
            this.setState(State.EXPECT_NAME)
            this.storeTypedChar(CharType.OPERATOR)
            this.storeField()
        }
    }
    inStateExpectAliasDelimiter() {
        if (this.char.isAliasDelimiter()) {
            this.storeTypedChar(CharType.OPERATOR)
            this.setState(State.EXPECT_ALIAS)
        } else {
            this.storeTypedChar(CharType.ERROR)
            this.setErrorState("invalid character, expected alias delimiter", 5)
        }
    }
}

export { Parser, tokenTypes, State, CHARS }