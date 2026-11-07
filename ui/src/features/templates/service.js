import HTTP from '@/utils/http'

const http = new HTTP()

export class TemplateService {
    list = () => http.Get('ui/v1/dashboard-templates')
    create = (slug, data) => http.Post(`ui/v1/dashboard-templates/${slug}`, data)
}
