# AutoFix — Project Progress

## Status: In Progress

## Completed Models
- autofix.car ✅
- autofix.service.reception ✅
- autofix.work.order ✅
- autofix.work.order.expense ✅
- autofix.petty.cash ✅

## Pending
- Invoicing: ربط service.reception بـ account.move
- Management Dashboard: إحصائيات المدير

## Standard Modules Used
base, mail, hr

## Key Decisions
- customer_rank domain اتشال لأن sale module مش installed
- work_order_expense اتحط كـ lines جوا work_order مش model مستقل
- petty cash بدون state machine لأن المدير بيسجل بنفسه
- mechanics بيتمثلوا بـ hr.employee مش res.partner
