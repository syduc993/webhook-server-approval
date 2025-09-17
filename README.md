1. Lark Platform ──POST──► handle_lark_webhook()
                              │
2. Extract & Filter ◄─────────┤
                              │
3. event_bus.publish("approval.instance.updated", data)
                              │
4. EventBus ◄─────────────────┘
    │
    ├─ Save to event_history[]
    │
    ├─ Find registered handlers for "approval.instance.updated"
    │
    └─ asyncio.gather() ──┬──► _run_handler_safe(qr_handler, data)
                          │      │
                          │      └──► QRHandler.handle() ──► Generate QR
                          │
                          └──► _run_handler_safe(validation_handler, data)  
                                 │
                                 └──► ValidationHandler.handle() ──► Send Alert
5. Results ──► Log success/failure cho mỗi handler



4. EventBus ──► asyncio.gather() ──┬──► _run_handler_safe(qr_handler, data)
                                   │      │
                                   │      └──► QRHandler.handle() 
                                   │             │
                                   │             ▼
                                   │      ┌─────────────────────────────┐
                                   │      │    QR Generation Flow       │
                                   │      ├─────────────────────────────┤
                                   │      │ 1. Extract instance_code    │
                                   │      │    ↓                        │
                                   │      │ 2. lark_service.get_instance(instance_code)
                                   │      │    ↓ (API Call)             │
                                   │      │ 3. Lark API ──► Instance Data
                                   │      │    ↓                        │
                                   │      │ 4. Check NODE_CONFIG        │
                                   │      │    ├─ Valid Node? ──► Continue
                                   │      │    └─ Invalid? ──► Skip & Return
                                   │      │    ↓                        │
                                   │      │ 5. cache_service.check()    │
                                   │      │    key: "qr:{instance}:{node}"
                                   │      │    ├─ Exists? ──► Skip (Duplicate)
                                   │      │    └─ Not exists? ──► Continue
                                   │      │    ↓                        │
                                   │      │ 6. amount_detector.extract()│
                                   │      │    ──► Parse amount from form
                                   │      │    ↓                        │
                                   │      │ 7. vietqr_service.generate()│
                                   │      │    ──► VietQR API Call     │
                                   │      │    ──► Get QR image bytes  │
                                   │      │    ↓                        │
                                   │      │ 8. lark_service.upload_image()
                                   │      │    ──► Lark API ──► file_code
                                   │      │    ↓                        │
                                   │      │ 9. lark_service.post_comment()
                                   │      │    ──► Post QR to approval  │
                                   │      │    ↓                        │
                                   │      │10. cache_service.set()      │
                                   │      │    ──► Mark QR created (15min TTL)
                                   │      │    ↓                        │
                                   │      │✅ Return success            │
                                   │      └─────────────────────────────┘
                                   │
                                   └──► _run_handler_safe(validation_handler, data)
                                          │
                                          └──► ValidationHandler.handle()
                                                 │
                                                 ▼
                                        ┌─────────────────────────────┐
                                        │   Validation & Alert Flow   │
                                        ├─────────────────────────────┤
                                        │ 1. Extract instance_code    │
                                        │    ↓                        │
                                        │ 2. lark_service.get_instance()
                                        │    ↓ (API Call)             │
                                        │ 3. Lark API ──► Instance Data
                                        │    ↓                        │
                                        │ 4. validation_service.validate()
                                        │    ├─ Check amount consistency
                                        │    ├─ Verify required fields│
                                        │    ├─ Business rule validation
                                        │    └─ Return errors[]       │
                                        │    ↓                        │
                                        │ 5. Check validation results │
                                        │    ├─ No errors? ──► Skip & Return
                                        │    └─ Has errors? ──► Continue
                                        │    ↓                        │
                                        │ 6. cache_service.check()    │
                                        │    key: "alert:{instance}:{hash}"
                                        │    ├─ Exists? ──► Skip (Duplicate)
                                        │    └─ Not exists? ──► Continue
                                        │    ↓                        │
                                        │ 7. notification_coordinator.send()
                                        │    ──► Format alert message │
                                        │    ↓                        │
                                        │ 8. lark_webhook_service.send()
                                        │    ──► Call Lark Bot API   │
                                        │    ──► Send to user/group  │
                                        │    ↓                        │
                                        │ 9. cache_service.set()      │
                                        │    ──► Mark alert sent (15min TTL)
                                        │    ↓                        │
                                        │✅ Return success            │
                                        └─────────────────────────────┘
