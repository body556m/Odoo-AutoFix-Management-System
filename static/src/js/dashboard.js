/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

class AutoFixDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            total_cars: 0,
            today_receptions: 0,
            open_work_orders: 0,
            done_work_orders_month: 0,
            month_revenue: 0,
            month_petty_cash: 0,
            month_wo_expenses: 0,
            stock_integration_count: 0,
            stock_integration_qty: 0,
            open_work_orders_list: [],
            mechanic_performance: [],
        });

        onWillStart(async () => {
            await this.fetchData();
        });
    }

    async fetchData() {
        const data = await this.orm.call(
            "autofix.service.reception",
            "get_dashboard_data",
            [],
        );
        Object.assign(this.state, data);
    }

    // --- Navigation helpers ---

    openCars() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Cars",
            res_model: "autofix.car",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openTodayReceptions() {
        const today = new Date().toISOString().split("T")[0];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Today's Receptions",
            res_model: "autofix.service.reception",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["date_received", "=", today]],
            target: "current",
        });
    }

    openOpenWorkOrders() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Open Work Orders",
            res_model: "autofix.work.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "in", ["pending", "in_progress"]]],
            target: "current",
        });
    }

    openDoneWorkOrdersMonth() {
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
            .toISOString().split("T")[0];
        const todayStr = today.toISOString().split("T")[0];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Completed Work Orders (This Month)",
            res_model: "autofix.work.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["state", "=", "done"],
                ["write_date", ">=", firstDay],
                ["write_date", "<=", todayStr],
            ],
            target: "current",
        });
    }

    openMonthRevenue() {
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
            .toISOString().split("T")[0];
        const todayStr = today.toISOString().split("T")[0];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Paid Invoices (This Month)",
            res_model: "account.move",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["move_type", "=", "out_invoice"],
                ["payment_state", "=", "paid"],
                ["invoice_date", ">=", firstDay],
                ["invoice_date", "<=", todayStr],
            ],
            target: "current",
        });
    }

    openMonthPettyCash() {
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
            .toISOString().split("T")[0];
        const todayStr = today.toISOString().split("T")[0];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Petty Cash (This Month)",
            res_model: "autofix.petty.cash",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["date", ">=", firstDay],
                ["date", "<=", todayStr],
            ],
            target: "current",
        });
    }

    openMonthWoExpenses() {
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
            .toISOString().split("T")[0];
        const todayStr = today.toISOString().split("T")[0];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Work Orders (This Month)",
            res_model: "autofix.work.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["create_date", ">=", firstDay],
                ["create_date", "<=", todayStr],
            ],
            target: "current",
        });
    }

    openStockIntegration() {
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1)
            .toISOString().split("T")[0];
        const todayStr = today.toISOString().split("T")[0];
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Stock Integration (This Month)",
            res_model: "stock.move",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [
                ["create_date", ">=", firstDay],
                ["create_date", "<=", todayStr],
                ["name", "ilike", "AutoFix WO:"],
            ],
            target: "current",
        });
    }

    getStateLabel(state) {
        const labels = {
            pending: "Pending",
            in_progress: "In Progress",
        };
        return labels[state] || state;
    }

    formatCurrency(value) {
        return parseFloat(value || 0).toLocaleString("en-US", {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }
}

AutoFixDashboard.template = "autofix.AutoFixDashboard";
registry.category("actions").add("autofix_dashboard", AutoFixDashboard);
