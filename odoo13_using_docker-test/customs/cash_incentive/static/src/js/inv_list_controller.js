/* @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { listView } from '@web/views/list/list_view';
import { useService } from "@web/core/utils/hooks";

class ImportInvController extends ListController {
    setup() {
        super.setup();
        this.action = useService("action");
    }

    uploadInv() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Upload Invoice',
            res_model: 'upload.invoice.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
        });

    }
};
export const InvUpload={
    ...listView,
    Controller: ImportInvController,
}

registry.category("views").add("inv_list_controller", InvUpload);
