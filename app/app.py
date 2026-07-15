from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os
import time

app = Flask(__name__)
app.secret_key = "highly-secure-isolated-environment-cryptographic-token"

ADMIN_FILE = os.path.join(os.path.dirname(__file__), 'admin_registry.json')
CARD_FILE = os.path.join(os.path.dirname(__file__), 'card_registry.json')

def load_json_file(filepath):
    if not os.path.exists(filepath):
        return {} if 'admin' in filepath else []
    with open(filepath, 'r') as f:
        return json.load(f)

def save_json_file(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, indent=2, fp=f)

LIVE_TRANSACTIONS = []

@app.route('/')
def user_portal():
    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        data = request.json or request.form
        username = data.get('username')
        password = data.get('password')
        
        admin_data = load_json_file(ADMIN_FILE)
        if username == admin_data.get('username') and password == admin_data.get('password'):
            session['admin_logged_in'] = True
            session.modified = True 
            return jsonify({"status": "success", "redirect": url_for('admin_portal')})
        else:
            return jsonify({"status": "error", "message": "Invalid Super Admin credentials!"}), 401
            
    return render_template('login.html')

@app.route('/admin')
def admin_portal():
    if 'admin_logged_in' not in session or session['admin_logged_in'] is not True:
        return redirect(url_for('admin_login'))
    return render_template('admin.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/send_money', methods=['POST'])
def send_money():
    data = request.json
    username = data.get('username')
    bank_account = data.get('bank_account')
    secure_code = data.get('secure_code')
    recipient_name = data.get('recipient_name')
    recipient_card = data.get('recipient_card')
    
    try:
        amount = float(data.get('amount', 0))
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid currency value amount."}), 400
    
    if not all([username, bank_account, secure_code, recipient_name, recipient_card, amount]) or amount <= 0:
        return jsonify({"status": "error", "message": "All transaction parameters must be fully met!"}), 400

    cards = load_json_file(CARD_FILE)
    
    sender = next((c for c in cards if c['card_number'] == bank_account), None)
    if not sender or sender['holder'].lower() != username.lower():
        return jsonify({"status": "rejected", "message": "Pre-Filter Failure: Sender Account Identity Mismatch!"}), 403
    if sender['secure_code'] != secure_code:
        return jsonify({"status": "rejected", "message": "Pre-Filter Failure: Authentication Pin Mismatch!"}), 403
    if sender['status'] == "FROZEN":
        return jsonify({"status": "rejected", "message": "Pre-Filter Failure: Originating Card is FROZEN!"}), 403
    if sender.get('balance', 0) < amount:
        return jsonify({"status": "rejected", "message": "Pre-Filter Failure: Insufficient funds available!"}), 403

    recipient = next((c for c in cards if c['card_number'] == recipient_card), None)
    if not recipient or recipient['holder'].lower() != recipient_name.lower():
        return jsonify({"status": "rejected", "message": "Pre-Filter Failure: Target Recipient Identity Verification Failed!"}), 403
    if recipient['status'] == "FROZEN":
        return jsonify({"status": "rejected", "message": "Pre-Filter Failure: Target Recipient Account is Locked!"}), 403

    if bank_account == recipient_card:
        return jsonify({"status": "rejected", "message": "Pre-Filter Failure: Cannot execute self-loop transactions."}), 403

    is_fraud = "FRAUD" if amount > 10000 else "CLEAN"

    if is_fraud == "CLEAN":
        sender['balance'] = round(sender.get('balance', 0) - amount, 2)
        recipient['balance'] = round(recipient.get('balance', 0) + amount, 2)
        save_json_file(CARD_FILE, cards)

    transaction_payload = {
        "timestamp": time.time(),
        "sender": sender['holder'],
        "sender_account": bank_account,
        "recipient": recipient['holder'],
        "recipient_account": recipient_card,
        "amount": amount,
        "status": is_fraud
    }

    LIVE_TRANSACTIONS.insert(0, transaction_payload)
    
    if is_fraud == "FRAUD":
        return jsonify({"status": "rejected", "message": "KServe Core: Highly Probabilistic Anomalous Threat Flagged! Transaction Blocked."}), 403
        
    return jsonify({"status": "success", "message": f"Successfully transferred ${amount:,.2f} to {recipient['holder']}!"})

# --- SUPER ADMIN UPDATE FLOW (WITH PRIMARY KEY RE-ASSIGNMENT MODES) ---

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    return jsonify(LIVE_TRANSACTIONS)

@app.route('/api/registry', methods=['GET', 'POST'])
def manage_registry():
    cards = load_json_file(CARD_FILE) #this is the real file containing real data
    if request.method == 'POST':
        data = request.json #data sent by the browser
        original_card_num = data.get("original_card_number")
        new_card_num = data.get("card_number")
        
        # Check if we are upgrading an existing key vs creating a raw entry
        target_card = None
        if original_card_num:
            target_card = next((c for c in cards if c['card_number'] == original_card_num), None)
            
        if target_card:
            target_card['holder'] = data.get("holder")
            target_card['secure_code'] = data.get("secure_code")
            target_card['card_number'] = new_card_num  # Key updated safely
            msg = "Card details and identification token updated successfully!"
        else:
            # Create a completely clean data node definition 
            new_card = {
                "card_number": new_card_num,
                "holder": data.get("holder"),
                "secure_code": data.get("secure_code"),
                "status": "ACTIVE",
                "balance": 1000.00
            }
            cards.append(new_card)
            msg = "New identity segment provisioned into database array registry."
            
        save_json_file(CARD_FILE, cards)
        return jsonify({"status": "success", "message": msg})
    
    return jsonify(cards)
#show users informations along with their transactions
@app.route('/api/user_analytics/<card_num>', methods=['GET'])
def get_user_analytics(card_num):
    cards = load_json_file(CARD_FILE)
    user_card = next((c for c in cards if c['card_number'] == card_num), None)
    if not user_card:
        return jsonify({"status": "error", "message": "Account missing"}), 404
        
    sent = sum(t['amount'] for t in LIVE_TRANSACTIONS if t['sender_account'] == card_num and t['status'] == "CLEAN")
    received = sum(t['amount'] for t in LIVE_TRANSACTIONS if t['recipient_account'] == card_num and t['status'] == "CLEAN")
    
    return jsonify({
        "holder": user_card['holder'],
        "card": card_num,
        "current_balance": user_card.get('balance', 0),
        "total_sent": sent,
        "total_received": received
    })
#Searching for someone(id bank)
@app.route('/api/registry/toggle/<card_num>', methods=['POST'])
def toggle_card(card_num):
    cards = load_json_file(CARD_FILE)
    card = next((c for c in cards if c['card_number'] == card_num), None)
    if card:
        card['status'] = "FROZEN" if card['status'] == "ACTIVE" else "ACTIVE"
        save_json_file(CARD_FILE, cards)
        return jsonify({"status": "success", "message": f"State set to {card['status']}"})
    return jsonify({"status": "error", "message": "Card not found"}), 404
#creates a new updated list
@app.route('/api/registry/delete/<card_num>', methods=['DELETE'])
def delete_card(card_num):
    cards = load_json_file(CARD_FILE)
    updated_cards = [c for c in cards if c['card_number'] != card_num]
    save_json_file(CARD_FILE, updated_cards)
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)