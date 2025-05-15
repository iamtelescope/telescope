import {getDefaultIfUndefined} from "@/utils/utils";

class SavedView {
    constructor(data) {
        this.slug = data.slug
        this.name = data.name
        this.scope = data.scope
        this.shared = data.shared
        this.description = data.description
        this.user = data.user
        this.data = data.data
        this.permissions = getDefaultIfUndefined(data.permissions, [])
        this.kind = data.kind
    }

    isEditable() {
        if (this.permissions.includes('edit')) {
            return true
        } else {
            return false
        }
    }
}

export {SavedView}
