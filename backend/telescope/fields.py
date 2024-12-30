from enum import Enum

DOT = "."
DOUBLE_QUOTE = '"'
SINGLE_QUOTE = "'"
MODIFIER_OPERATOR = "|"
MODIFIER_ARGUMENT_DELIMITER = ","
FIELDS_DELIMITER = ","
SPACE = " "
ALIAS_DELIMITER = " "
COLON = ":"
SLASH = "/"
BACKSLASH = "\\"
BRACKET_OPEN = "("
BRACKET_CLOSE = ")"
UNDERSCORE = "_"
VALID_ALIAS_OPERATOR = "as"


class ParserError(Exception):
    def __init__(
        self,
        message,
        errno,
    ):
        self.message = message
        self.errno = errno

    def __str__(self):
        return self.message

    def __repr__(self):
        return str(self)


class State(Enum):
    ERROR = "Error"
    FIELD = "Name"
    EXPECT_FIELD = "ExpectField"
    EXPECT_ALIAS = "ExpectAlias"
    EXPECT_ALIAS_OPERATOR = "ExpectAliasOperator"
    EXPECT_ALIAS_DELIMITER = "ExpectAliasDelimiter"
    EXPECT_MODIFIER = "ExpectModifier"
    MODIFIER = "Modifier"
    MODIFIER_COMPLETE = "ModifierComplete"
    MODIFIER_OPERATOR = "ModifierOperator"
    MODIFIER_ARGUMENT = "ModifierArgument"
    MODIFIER_ARGUMENT_DOUBLE_QUOTED = "ModifierArgumentDoubleQuoted"
    MODIFIER_ARGUMENT_SINGLE_QUOTED = "ModifierArgumentSingleQuoted"
    EXPECT_MODIFIER_ARGUMENT = "ExpectModifierArgument"
    EXPECT_MODIFIER_ARGUMENT_DELIMITER = "ExpectModifierArgumentDelimiter"
    SINGLE_QUOTED_ARGUMENT = "SingleQuotedArgument"
    DOUBLE_QUOTED_ARGUMENT = "DoubleQuotedArgument"
    MODIFIER_ARGUMENT_DELIMITER = "ArgumentDelimiter"


class Char:
    def __init__(
        self,
        value,
        pos,
    ):
        self.value = value
        self.pos = pos

    def is_field_value(self):
        return (
            self.value.isalnum()
            or self.value == UNDERSCORE
            or self.value == DOT
            or self.value == COLON
            or self.value == SLASH
        )

    def is_modifier_argument_value(self):
        return (
            self.value != MODIFIER_ARGUMENT_DELIMITER
            and self.value != BRACKET_OPEN
            and self.value != BRACKET_CLOSE
        )

    def is_modifier_double_quoted_argument_value(self):
        return not self.is_double_quote()

    def is_modifier_single_quoted_argument_value(self):
        return not self.is_single_quote()

    def is_modifier_value(self):
        return self.value.isalnum() or self.value == UNDERSCORE

    def is_alias_char(self):
        return self.value in ["A", "a", "S", "s"]

    def is_bracket_open(self):
        return self.value == BRACKET_OPEN

    def is_bracket_close(self):
        return self.value == BRACKET_CLOSE

    def is_double_quote(self):
        return self.value == DOUBLE_QUOTE

    def is_single_quote(self):
        return self.value == SINGLE_QUOTE

    def is_modifier_operator(self):
        return self.value == MODIFIER_OPERATOR

    def is_modifier_argument_delimiter(self):
        return self.value == MODIFIER_ARGUMENT_DELIMITER

    def is_fields_delimiter(self):
        return self.value == FIELDS_DELIMITER

    def is_alias_delimiter(self):
        return self.value == ALIAS_DELIMITER

    def is_space(self):
        return self.value == SPACE

    def is_backslash(self):
        return self.value == BACKSLASH


class Parser:
    def __init__(
        self,
    ):
        self.pos = 0
        self.char = Char("", -1)
        self.state = State.EXPECT_FIELD
        self.error_text = ""
        self.errno = 0
        self.field = ""
        self.alias = ""
        self.alias_operator = ""
        self.modifier = ""
        self.modifier_argument = ""
        self.modifier_argument_type = "auto"
        self.modifiers = []
        self.modifier_arguments = []
        self.fields = []

    def set_text(self, text):
        self.text = text

    def store_field(self):
        self.fields.append(
            {
                "name": self.field,
                "modifiers": self.modifiers,
                "alias": self.alias,
            }
        )
        self.reset_data()

    def store_modifier(self):
        self.modifiers.append(
            {
                "name": self.modifier,
                "arguments": self.modifier_arguments,
            }
        )
        self.reset_modifier()

    def store_argument(self):
        value = self.modifier_argument
        if self.modifier_argument_type == "auto":
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
        self.modifier_arguments.append(value)
        self.reset_modifier_argument()

    def set_char(self, char):
        self.char = char

    def set_state(self, state):
        self.state = state

    def reset_modifier(self):
        self.modifier = ""
        self.modifier_arguments = []
        self.modifier_argument = ""

    def reset_field(self):
        self.field = ""

    def reset_alias_operator(self):
        self.alias_operator = ""

    def reset_alias(self):
        self.alias = ""

    def reset_modifiers(self):
        self.modifiers = []

    def reset_modifier_argument(self):
        self.modifier_argument = ""
        self.modifier_argument_type = "auto"

    def reset_data(self):
        self.reset_field()
        self.reset_alias()
        self.reset_modifier()
        self.reset_modifiers()
        self.reset_alias_operator()

    def set_error_state(self, error_text, errno):
        self.state = State.ERROR
        self.error_text = error_text
        self.errno = errno
        if self.char:
            self.error_text += (
                f" [char {self.char.value} at pos {self.char.pos}], errno={errno}"
            )

    def extend_field(self):
        self.field += self.char.value

    def extend_modifier(self):
        self.modifier += self.char.value

    def extend_modifier_argument(self):
        self.modifier_argument += self.char.value

    def extend_alias(self):
        self.alias += self.char.value

    def extend_alias_operator(self):
        self.alias_operator += self.char.value

    def parse(self, text):
        self.set_text(text)
        for c in text:
            if self.state == State.ERROR:
                break
            self.set_char(Char(c, self.pos))

            match self.state:
                case State.EXPECT_FIELD:
                    self.in_state_expect_field()
                case State.FIELD:
                    self.in_state_field()
                case State.EXPECT_ALIAS:
                    self.in_state_expect_alias()
                case State.EXPECT_ALIAS_OPERATOR:
                    self.in_state_expect_alias_operator()
                case State.EXPECT_ALIAS_DELIMITER:
                    self.in_state_expect_alias_delimiter()
                case State.EXPECT_MODIFIER:
                    self.in_state_expect_modifier()
                case State.EXPECT_MODIFIER_ARGUMENT:
                    self.in_state_expect_modifier_argument()
                case State.MODIFIER:
                    self.in_state_modifier()
                case State.MODIFIER_ARGUMENT:
                    self.in_state_modifier_argument()
                case State.MODIFIER_COMPLETE:
                    self.in_state_modifier_complete()
                case State.MODIFIER_ARGUMENT_DOUBLE_QUOTED:
                    self.in_state_modifier_argument_double_quoted()
                case State.MODIFIER_ARGUMENT_SINGLE_QUOTED:
                    self.in_state_modifier_argument_single_quoted()
                case State.EXPECT_MODIFIER_ARGUMENT_DELIMITER:
                    self.in_state_expect_modifier_argument_delimiter()
                case _:
                    self.set_error_state(f"unknown state: {self.state}", 1)
            self.pos += 1

        if self.state == State.ERROR:
            raise ParserError(
                message=self.error_text,
                errno=self.errno,
            )

        self.in_state_last_char()

        if self.state == State.ERROR:
            raise ParserError(
                message=self.error_text,
                errno=self.errno,
            )

    def in_state_last_char(self):
        if self.state == State.FIELD:
            self.store_field()
        elif self.state == State.EXPECT_ALIAS:
            if self.alias:
                self.store_field()
            else:
                self.set_error_state(
                    "unexpected end of alias. Expected alias value", 13
                )
        elif (
            self.state == State.EXPECT_ALIAS_OPERATOR
            or self.state == State.EXPECT_ALIAS_DELIMITER
        ):
            self.set_error_state("unexpected end of alias. Expected alias value", 14)
        elif self.state == State.MODIFIER:
            if self.modifier:
                self.store_modifier()
            if self.field:
                self.store_field()
        elif self.state == State.MODIFIER_COMPLETE:
            self.store_modifier()
            self.store_field()
        elif (
            self.state == State.MODIFIER_ARGUMENT_DOUBLE_QUOTED
            or self.state == State.MODIFIER_ARGUMENT_SINGLE_QUOTED
        ):
            self.set_error_state("unexpected end of quoted argument value", 12)
        elif self.state == State.EXPECT_MODIFIER_ARGUMENT_DELIMITER:
            self.set_error_state("unexpected end of arguments list", 15)

    def in_state_expect_field(self):
        if self.char.is_space():
            return
        elif self.char.is_field_value():
            self.extend_field()
            self.set_state(State.FIELD)
        else:
            self.set_error_state("invalid character", 2)
            return

    def in_state_field(self):
        if self.char.is_space():
            self.set_state(State.EXPECT_ALIAS_OPERATOR)
        elif self.char.is_field_value():
            self.extend_field()
        elif self.char.is_fields_delimiter():
            self.set_state(State.EXPECT_FIELD)
            self.store_field()
        elif self.char.is_modifier_operator():
            self.set_state(State.EXPECT_MODIFIER)
        else:
            self.set_error_state("invalid character", 6)

    def in_state_expect_modifier(self):
        if self.char.is_modifier_value():
            self.extend_modifier()
            self.set_state(State.MODIFIER)
        else:
            self.set_error_state("invalid character, expected modifier", 7)

    def in_state_modifier(self):
        if self.char.is_modifier_value():
            self.extend_modifier()
        elif self.char.is_fields_delimiter():
            self.store_modifier()
            self.store_field()
            self.set_state(State.EXPECT_FIELD)
        elif self.char.is_modifier_operator():
            self.store_modifier()
            self.set_state(State.EXPECT_MODIFIER)
        elif self.char.is_space():
            self.set_state(State.EXPECT_ALIAS_OPERATOR)
        elif self.char.is_bracket_open():
            self.set_state(State.EXPECT_MODIFIER_ARGUMENT)
        elif self.char.is_bracket_close():
            self.store_argument()
            self.store_modifier()
            raise ValueError("unsupported close bracket")
        else:
            raise ValueError("unsupported char in modifier")

    def in_state_expect_modifier_argument(self):
        if self.char.is_space():
            return
        if self.char.is_double_quote():
            self.modifier_argument_type = "str"
            self.set_state(State.MODIFIER_ARGUMENT_DOUBLE_QUOTED)
        elif self.char.is_single_quote():
            self.modifier_argument_type = "str"
            self.set_state(State.MODIFIER_ARGUMENT_SINGLE_QUOTED)
        elif self.char.is_modifier_argument_value():
            self.extend_modifier_argument()
            self.set_state(State.MODIFIER_ARGUMENT)

    def in_state_modifier_argument(self):
        if self.char.is_modifier_argument_delimiter():
            self.store_argument()
            self.set_state(State.EXPECT_MODIFIER_ARGUMENT)
        elif self.char.is_modifier_argument_value():
            self.extend_modifier_argument()
        elif self.char.is_bracket_close():
            self.store_argument()
            self.set_state(State.MODIFIER_COMPLETE)

    def in_state_expect_modifier_argument_delimiter(self):
        if self.char.is_modifier_argument_delimiter():
            self.set_state(State.EXPECT_MODIFIER_ARGUMENT)
        elif self.char.is_bracket_close():
            self.set_state(State.MODIFIER_COMPLETE)
        else:
            self.set_error_state(
                "invalid character. Expected bracket close or modifier argument delimiter",
                9,
            )
            return

    def in_state_modifier_argument_double_quoted(self):
        if self.char.is_backslash():
            next_pos = self.char.pos + 1
            try:
                next_char = self.text[next_pos]
            except IndexError:
                self.extend_modifier_argument()
            else:
                if next_char != DOUBLE_QUOTE:
                    self.extend_modifier_argument()
        elif self.char.is_modifier_double_quoted_argument_value():
            self.extend_modifier_argument()
        elif self.char.is_double_quote():
            prev_pos = self.char.pos - 1
            if self.text[prev_pos] == BACKSLASH:
                self.extend_modifier_argument()
            else:
                self.store_argument()
                self.set_state(State.EXPECT_MODIFIER_ARGUMENT_DELIMITER)
        else:
            self.set_error_state("invalid character", 10)
            return

    def in_state_modifier_argument_single_quoted(self):
        if self.char.is_backslash():
            next_pos = self.char.pos + 1
            try:
                next_char = self.text[next_pos]
            except IndexError:
                self.extend_modifier_argument()
            else:
                if next_char != SINGLE_QUOTE:
                    self.extend_modifier_argument()
        elif self.char.is_modifier_single_quoted_argument_value():
            self.extend_modifier_argument()
        elif self.char.is_single_quote():
            prev_pos = self.char.pos - 1
            if self.text[prev_pos] == BACKSLASH:
                self.extend_modifier_argument()
            else:
                self.store_argument()
                self.set_state(State.EXPECT_MODIFIER_ARGUMENT_DELIMITER)
        else:
            self.set_error_state("invalid character", 10)
            return

    def in_state_modifier_complete(self):
        if self.char.is_space():
            self.store_modifier()
            self.set_state(State.EXPECT_ALIAS_OPERATOR)
        elif self.char.is_fields_delimiter():
            self.store_modifier()
            self.store_field()
            self.set_state(State.EXPECT_FIELD)
        elif self.char.is_modifier_operator():
            self.store_modifier()
            self.set_state(State.EXPECT_MODIFIER)
        else:
            self.set_error_state("invalid character", 8)

    def in_state_expect_alias_operator(self):
        if self.char.is_space():
            return
        elif self.char.is_alias_char():
            self.extend_alias_operator()
            if len(self.alias_operator) < 2:
                return
            if len(self.alias_operator) == 2:
                if self.alias_operator.lower() != VALID_ALIAS_OPERATOR:
                    self.set_error_state("invalid character", 3)
                else:
                    self.set_state(State.EXPECT_ALIAS_DELIMITER)
                    self.reset_alias_operator()
            else:
                return
        else:
            self.set_error_state("invalid character, expected alias operator", 4)

    def in_state_expect_alias(self):
        if self.char.is_space():
            return
        elif self.char.is_field_value():
            self.extend_alias()
        elif self.char.is_fields_delimiter():
            self.set_state(State.EXPECT_FIELD)
            self.store_field()

    def in_state_expect_alias_delimiter(self):
        if self.char.is_alias_delimiter():
            self.set_state(State.EXPECT_ALIAS)
        else:
            self.set_error_state("invalid character, expected alias delimiter", 5)


def parse(source, text):
    parser = Parser()
    parser.parse(text)
    data = []
    for field in parser.fields:
        source_field_name = field["name"].split(":")[0]
        if source_field_name not in source._fields:
            raise ParserError(
                message=f"Source have no '{source_field_name}' field", errno=100
            )

        source_field = source._fields[source_field_name]
        titled_name = (
            field["name"].title() if not ":" in field["name"] else field["name"]
        )
        display_name = field["alias"] or source_field.get("display_name") or titled_name
        data.append(
            {
                "name": field["name"],
                "root_name": source_field["name"],
                "type": source_field["type"],
                "display_name": display_name,
                "modifiers": field["modifiers"],
            }
        )
    return data
