import getCSRFToken from "@/utils/csrf"
import UIResponse from "@/sdk/models/response"

class HTTP {
    Request = async (url, method, data) => {
        let response = new UIResponse()
        try {
            let requestOptions = {
                method: method,
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                }
            }
            if (method == 'POST' || method == 'DELETE' || method == 'PATCH') {
                requestOptions.headers['X-CSRFToken'] = getCSRFToken()
            }
            if (data !== undefined) {
                requestOptions.body = JSON.stringify(data)
            }

            let r = await fetch(url, requestOptions)
            if (!r.ok) {
                throw Error(`failed to fetch ${r.url}. ${r.status}: ${r.statusText}`)
            } else {
                let data = await r.json()
                response.messages = data.messages
                response.errors = data.errors
                response.data = data.data
                response.validation = data.validation
                response.result = data.result
            }
        }
        catch (err) {
            response.result = false
            response.errors = [err.message]
        }
        return response
    }
    Get = async (url) => {
        return this.Request(url, 'GET')
    }
    Post = async (url, data) => {
        return this.Request(url, 'POST', data)
    }
    Patch = async (url, data) => {
        return this.Request(url, 'PATCH', data)
    }
    Delete = async (url) => {
        return this.Request(url, 'DELETE')
    }
}

export default HTTP