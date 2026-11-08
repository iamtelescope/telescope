import { useConfirm } from 'primevue/useconfirm'

// Asks before a destructive action, in the dialog App.vue mounts (group "app").
// const confirmDelete = useConfirmDestructive(); confirmDelete({ message, acceptLabel: 'Delete', accept })
export const useConfirmDestructive = () => {
    const confirm = useConfirm()
    return ({ header = 'Are you sure?', message, acceptLabel = 'Delete', accept }) =>
        confirm.require({
            group: 'app',
            header,
            message,
            icon: 'pi pi-exclamation-triangle',
            rejectProps: { label: 'Cancel', severity: 'secondary', outlined: true, size: 'small' },
            acceptProps: { label: acceptLabel, severity: 'danger', size: 'small' },
            defaultFocus: 'reject',
            accept,
        })
}
