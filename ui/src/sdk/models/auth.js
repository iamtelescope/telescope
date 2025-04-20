import { getDefaultIfUndefined } from '@/utils/utils'

class APIToken {
    constructor(data) {
        this.name = data.name
        this.created = data.created
        this.token = data.token
    }
}

export { APIToken }
