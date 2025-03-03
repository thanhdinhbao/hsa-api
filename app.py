from flask import Flask, request, jsonify
import json
import requests

app = Flask(__name__)

TELEGRAM_BOT_TOKEN = "8006256969:AAGwNNZvejgOBdEUwhb6X2amomGh6weEFdY"
TELEGRAM_CHAT_ID = "1140937151"

def get_token(id, passwd):
    url = "https://api.hsa.edu.vn/accounts/sign-in"
    payload = json.dumps({
        "id": id,
        "password": passwd
    })
    headers = {
        # ... (keeping your original headers)
        'Accept': 'application/json, text/plain, */*',
        # ... rest of your headers
    }
    response = requests.post(url, headers=headers, data=payload)
    data = response.json()
    return data.get("token")

def extract_ids(response):
    return [{"id": item["id"], "name": item["name"]} for item in response]

def get_available_locations(token, id):
    if id == '83':
        batch_name = "HSA 505"
    elif id == '84':
        batch_name = "HSA 506"
    else:
        batch_name = f"ID {id} không xác định"
    
    url = f"https://api.hsa.edu.vn/exam/views/registration/available-location?batchId={id}"
    headers = {
        "Authorization": f"Bearer {token}",
        # ... rest of your headers
    }
    response = requests.get(url, headers=headers)
    response_data = json.loads(response.text)
    id_list = extract_ids(response_data)
    return id_list, batch_name

def get_available_slots(location_id, loc_place, token, batchname):
    url = f"https://api.hsa.edu.vn/exam/views/registration/available-slot?locationId={location_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        # ... rest of your headers
    }
    response = requests.get(url, headers=headers)
    data = response.json()
    
    results = []
    for slot in data:
        registered = slot["registeredSlots"]
        total_seats = slot["numberOfSeats"]
        
        if registered < total_seats:
            available_slots = total_seats - registered
            message = {
                "batch": batchname,
                "slot": slot["name"],
                "location": loc_place,
                "date": slot["eventDateTime"][:10],
                "available_slots": available_slots,
                "code": slot["code"]
            }
            results.append(message)
            send_telegram_message(format_message(message))
    
    return results

def format_message(data):
    return f"📢 *Có slot trống!* 🎯\n\n" \
           f"📍 *Đợt thi:* {data['batch']}\n" \
           f"📍 *Ca thi:* {data['slot']}\n" \
           f"📍 *Địa điểm:* {data['location']}\n" \
           f"📅 *Ngày thi:* {data['date']}\n" \
           f"🪑 *Số chỗ còn trống:* {data['available_slots']}\n" \
           f"🔗 *Mã ca thi:* {data['code']}"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    response = requests.post(url, json=payload)
    return response.json()

@app.route('/check_slots', methods=['POST'])
def check_slots():
    try:
        data = request.get_json()
        user_id = data.get('id', '0963864520')
        password = data.get('password', 'Nguyen000')
        batch_id = data.get('batch_id', '84')

        # Get token
        token = get_token(user_id, password)
        if not token:
            return jsonify({"error": "Failed to authenticate"}), 401

        # Get available locations
        locations, batch_name = get_available_locations(token, batch_id)
        
        # Check slots for each location
        all_results = []
        for location in locations:
            results = get_available_slots(location['id'], location['name'], token, batch_name)
            all_results.extend(results)

        return jsonify({
            "batch_name": batch_name,
            "available_slots": all_results,
            "total_available": len(all_results)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
