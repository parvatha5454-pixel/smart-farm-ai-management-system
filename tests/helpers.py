def login(client, user):
    with client.session_transaction() as s:
        s["user_id"] = user.id
        s["full_name"] = user.full_name
        s["role"] = user.role
