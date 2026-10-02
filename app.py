from flask import Flask, request, jsonify
import re
import base64

app = Flask(__name__)

# インメモリDB (テスト用アカウントを初期登録)
users = {
    "TaroYamada": {
        "user_id": "TaroYamada",
        "password": "PaSSwd4TY",
        "nickname": "たろー",
        "comment": "僕は元気です"
    }
}

def validate_user_id(user_id):
    if not user_id:
        return False
    if len(user_id) < 6 or len(user_id) > 20:
        return False
    if not re.match(r'^[a-zA-Z0-9]+$', user_id):
        return False
    return True

def validate_password(password):
    if not password:
        return False
    if len(password) < 8 or len(password) > 20:
        return False
    # 半角英数字記号 (空白と制御コードを除くASCII文字)
    if not re.match(r'^[\x21-\x7E]+$', password):
        return False
    return True

def get_auth(request):
    """AuthorizationヘッダーからBasic認証を取得"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Basic '):
        return None, None
    try:
        decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
        user_id, password = decoded.split(':', 1)
        return user_id, password
    except Exception:
        return None, None


@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json(silent=True) or {}

    user_id = data.get('user_id')
    password = data.get('password')

    # 必須チェック
    if not user_id or not password:
        return jsonify({
            "message": "Account creation failed",
            "cause": "Required user_id and password"
        }), 400

    # 長さチェック
    if not (6 <= len(user_id) <= 20) or not (8 <= len(password) <= 20):
        return jsonify({
            "message": "Account creation failed",
            "cause": "Input length is incorrect"
        }), 400

    # 文字種チェック
    if not re.match(r'^[a-zA-Z0-9]+$', user_id):
        return jsonify({
            "message": "Account creation failed",
            "cause": "Incorrect character pattern"
        }), 400

    if not re.match(r'^[\x21-\x7E]+$', password):
        return jsonify({
            "message": "Account creation failed",
            "cause": "Incorrect character pattern"
        }), 400

    # 重複チェック
    if user_id in users:
        return jsonify({
            "message": "Account creation failed",
            "cause": "Already same user_id is used"
        }), 400

    # ユーザー作成
    nickname = data.get('nickname', user_id)
    comment = data.get('comment', None)

    users[user_id] = {
        "user_id": user_id,
        "password": password,
        "nickname": nickname if nickname else user_id,
        "comment": comment
    }

    return jsonify({
        "message": "Account successfully created",
        "user": {
            "user_id": user_id,
            "nickname": users[user_id]["nickname"]
        }
    }), 200


@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    # 認証
    auth_user_id, auth_password = get_auth(request)
    if not auth_user_id or not auth_password:
        return jsonify({"message": "Authentication failed"}), 401

    if auth_user_id not in users or users[auth_user_id]["password"] != auth_password:
        return jsonify({"message": "Authentication failed"}), 401

    # ユーザー存在チェック
    if user_id not in users:
        return jsonify({"message": "No user found"}), 404

    user = users[user_id]
    user_data = {
        "user_id": user["user_id"],
        "nickname": user["nickname"] if user["nickname"] else user["user_id"]
    }
    if user.get("comment") is not None:
        user_data["comment"] = user["comment"]

    return jsonify({
        "message": "User details by user_id",
        "user": user_data
    }), 200


@app.route('/users/<user_id>', methods=['PATCH'])
def update_user(user_id):
    # 認証
    auth_user_id, auth_password = get_auth(request)
    if not auth_user_id or not auth_password:
        return jsonify({"message": "Authentication failed"}), 401

    if auth_user_id not in users or users[auth_user_id]["password"] != auth_password:
        return jsonify({"message": "Authentication failed"}), 401

    # 他のユーザーの更新は禁止
    if auth_user_id != user_id:
        return jsonify({"message": "No permission for update"}), 403

    # ユーザー存在チェック
    if user_id not in users:
        return jsonify({"message": "No user found"}), 404

    data = request.get_json(silent=True) or {}

    # user_id, password の変更禁止
    if 'user_id' in data or 'password' in data:
        return jsonify({
            "message": "User updation failed",
            "cause": "Not updatable user_id and password"
        }), 400

    nickname = data.get('nickname')
    comment = data.get('comment')

    # nickname と comment 両方なし
    if 'nickname' not in data and 'comment' not in data:
        return jsonify({
            "message": "User updation failed",
            "cause": "Required nickname or comment"
        }), 400

    # バリデーション
    if 'nickname' in data:
        if nickname is not None and len(nickname) > 30:
            return jsonify({
                "message": "User updation failed",
                "cause": "String length limit exceeded or containing invalid characters"
            }), 400
        # 制御コードチェック
        if nickname and re.search(r'[\x00-\x1F\x7F]', nickname):
            return jsonify({
                "message": "User updation failed",
                "cause": "String length limit exceeded or containing invalid characters"
            }), 400

    if 'comment' in data:
        if comment is not None and len(comment) > 100:
            return jsonify({
                "message": "User updation failed",
                "cause": "String length limit exceeded or containing invalid characters"
            }), 400
        if comment and re.search(r'[\x00-\x1F\x7F]', comment):
            return jsonify({
                "message": "User updation failed",
                "cause": "String length limit exceeded or containing invalid characters"
            }), 400

    # 更新
    user = users[user_id]
    if 'nickname' in data:
        # 空文字の場合はuser_idに戻す
        user["nickname"] = nickname if nickname else user_id
    if 'comment' in data:
        # 空文字の場合はクリア
        user["comment"] = comment if comment else None

    user_data = {
        "user_id": user["user_id"],
        "nickname": user["nickname"]
    }
    if user.get("comment") is not None:
        user_data["comment"] = user["comment"]

    return jsonify({
        "message": "User successfully updated",
        "user": user_data
    }), 200


@app.route('/close', methods=['POST'])
def close():
    # 認証
    auth_user_id, auth_password = get_auth(request)
    if not auth_user_id or not auth_password:
        return jsonify({"message": "Authentication failed"}), 401

    if auth_user_id not in users or users[auth_user_id]["password"] != auth_password:
        return jsonify({"message": "Authentication failed"}), 401

    # アカウント削除
    del users[auth_user_id]

    return jsonify({"message": "Account and user successfully removed"}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
