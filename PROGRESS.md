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
  - إضافة زرار "Print Invoices" في الـ tree view header لطباعة فواتير الطلبات المتعددة كـ PDF

## Pending
- Management Dashboard: إحصائيات المدير

## Standard Modules Used
base, mail, hr, account

## Key Decisions
- customer_rank domain اتشال لأن sale module مش installed
- work_order_expense اتحط كـ lines جوا work_order مش model مستقل
- petty cash بدون state machine لأن المدير بيسجل بنفسه
- mechanics بيتمثلوا بـ hr.employee مش res.partner
- الفواتير بتتعمل من account.move مباشرة — مفيش custom invoicing
- كل work order بيبقى سطر في الفاتورة (labor cost) + سطر لكل expense
