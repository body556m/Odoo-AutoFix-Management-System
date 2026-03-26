# AutoFix — Project Progress

## Status: In Progress

## Completed Models
- autofix.car ✅
- autofix.service.reception ✅
- autofix.work.order ✅
- autofix.work.order.expense ✅
- autofix.petty.cash ✅

## Completed Features
- Invoicing: ربط service.reception بـ account.move ✅
  - invoice_ids (Many2many) على service.reception
  - invoice_count (computed) + smart button لعرض الفواتير
  - action_create_invoice — بيعمل account.move تلقائي بأسطر الأجرة والمصاريف
  - action_view_invoices — بيفتح الفواتير المرتبطة
  - labor_cost على work.order — تكلفة الأجرة لكل أمر شغل
  - total_cost (computed) = labor_cost + total_expenses
  - زرار "Create Invoice" في header الـ form (يظهر لما state = done ومفيش فاتورة)
  - زرار "Create Invoices" في header الـ tree للطلبات المتعددة
  - account module اتضاف في depends
- PDF Report — Maintenance Invoice ✅
  - QWeb PDF report طباعة فاتورة الصيانة من form view
  - زرار "Print Invoice" في header الـ form (يظهر لما invoice_count > 0)
  - زرار "Print Invoices" في header الـ tree (بيفلتر الريكوردات اللي عليها فواتير)
  - بيعرض: بيانات العميل والعربية، الشكوى، الأعمال، جدول أوامر الشغل، تفاصيل المصاريف، الإجماليات
- Server Action — Create Invoices من الـ tree view (Action menu) ✅
- Management Dashboard — OWL component ✅
  - 7 KPI cards تفتح filtered list views لما تتضغط عليها
  - جدول الـ work orders المفتوحة
  - جدول أداء الميكانيكيين الشهر ده
  - default action للـ AutoFix menu
- Stock Integration — spare parts tracked from stock module ✅
  - autofix.work.order.part model (One2many)
  - part_ids, total_parts_cost, stock_move_ids على work.order
  - total_cost = labor_cost + total_expenses + total_parts_cost
  - action_done() creates stock.move + autofix.work.order.expense for each part
  - reorder point check creates purchase.order if qty_available < min_qty
  - stock and purchase modules added to depends

## Pending
- User Groups — Manager / Mechanic / Receptionist
- Cron — تقرير يومي للمدير
- HR Payroll — مرتبات الميكانيكيين (آخر feature)

## Standard Modules Used
base, mail, hr, account, stock, purchase

## Key Decisions
- customer_rank domain اتشال لأن sale module مش installed
- work_order_expense اتحط كـ lines جوا work_order مش model مستقل
- petty cash بدون state machine لأن المدير بيسجل بنفسه
- mechanics بيتمثلوا بـ hr.employee مش res.partner
- الفواتير بتتعمل من account.move مباشرة — مفيش custom invoicing
- كل work order بيبقى سطر في الفاتورة (labor cost) + سطر لكل expense

## Phase 2 Plan

### ترتيب التنفيذ
1. Management Dashboard ✅
2. PDF Report — فاتورة الصيانة ✅
3. Cron — تنبيه بعد 15 يوم / إلغاء تلقائي بعد 30 يوم لو ما اتدفعش ✅
4. Stock Integration — ربط work order بالمخزن ✅
5. User Groups — Manager / Mechanic / Receptionist
6. Cron — تقرير يومي للمدير
7. HR Payroll — مرتبات الميكانيكيين (آخر feature)

### Dashboard KPIs
- كام عربية مسجلة إجمالاً
- كام reception النهارده
- كام أمر شغل مفتوح
- كام أمر خلص الشهر ده
- إجمالي الإيرادات الشهر ده
- إجمالي النثريات الشهر ده
- إجمالي مصاريف الـ work orders الشهر ده
- جدول الـ work orders المفتوحة
- جدول أداء الميكانيكيين الشهر ده
