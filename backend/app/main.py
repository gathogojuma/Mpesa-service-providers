@app.get("/seed-demo-data")
async def seed_demo_data():
    """Smart seed endpoint that handles existing data."""
    db = SessionLocal()
    try:
        results = {"actions": []}

        # Check/create business
        business = db.query(Business).filter(Business.phone == "+254700000000").first()
        if not business:
            business = Business(name="Demo Bar", phone="+254700000000")
            db.add(business)
            db.commit()
            db.refresh(business)
            results["actions"].append("Created business")
        else:
            results["actions"].append(f"Business already exists: {business.id}")

        # Define users to create
        users_to_create = [
            ("Demo Manager", "+254700000001", "manager"),
            ("Demo Server 1", "+254700000002", "server"),
            ("Demo Server 2", "+254700000003", "server"),
            ("Demo Server 3", "+254700000004", "server"),
        ]

        for name, phone, role in users_to_create:
            existing = db.query(Staff).filter(Staff.phone == phone).first()
            if existing:
                # Update password in case it's wrong
                existing.pin_hash = get_password_hash("1234")
                existing.business_id = business.id
                existing.role = role
                existing.name = name
                db.commit()
                results["actions"].append(f"Updated existing user: {phone}")
            else:
                s = Staff(
                    name=name,
                    phone=phone,
                    pin_hash=get_password_hash("1234"),
                    role=role,
                    business_id=business.id
                )
                db.add(s)
                db.commit()
                results["actions"].append(f"Created user: {phone}")

        # Final check
        all_staff = db.query(Staff).all()
        results["total_staff"] = len(all_staff)
        results["staff_list"] = [
            {"id": s.id, "name": s.name, "phone": s.phone, "role": s.role, "business_id": s.business_id}
            for s in all_staff
        ]
        results["business_id"] = business.id
        results["status"] = "success"

        return results
    except Exception as e:
        return {"status": "error", "message": str(e), "type": type(e).__name__}
    finally:
        db.close()
