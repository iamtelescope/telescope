import { getDefaultIfUndefined } from '@/utils/utils'

class UIResponse {
    constructor() {
        this.data = {}
        this.errors = []
        this.messages = []
        this.result = false
        this.aborted = false
        this.validation = {
            result: true,
            fields: {},
            non_column: [],
        }
    }

    sendToastMessages(toast, lifetime) {
        lifetime = getDefaultIfUndefined(lifetime, 3000)

        for (const idx in this.messages) {
            toast.add({
                severity: 'success',
                summary: 'Success',
                detail: this.messages[idx],
                life: lifetime,
            })
        }
    }

    sendToastErrors(toast, lifetime) {
        lifetime = getDefaultIfUndefined(lifetime, 6000)

        for (const idx in this.errors) {
            toast.add({ severity: 'error', summary: 'Error', detail: this.errors[idx], life: lifetime })
        }
    }

    sendToast(toast, messagesLifetime, errorsLifetime) {
        this.sendToastMessages(toast, messagesLifetime)
        this.sendToastErrors(toast, errorsLifetime)
    }
}

export default UIResponse
