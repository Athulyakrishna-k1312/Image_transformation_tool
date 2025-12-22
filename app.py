from animegan import animegan_cartoonize
from flask import Flask, render_template, request, redirect, flash, url_for, session, send_file
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
import cv2
from cartoonize import cartoonize_image
from ghibli_style import ghibli_cartoonize
import numpy as np
import tempfile
from datetime import date,datetime, timedelta
import razorpay

# at top of app.py (after other imports)
from razorpay.errors import SignatureVerificationError
import hmac, hashlib

PRICES = {
    "Basic": 49,
    "Standard": 199,
    "Pro": 999,
    "Premium": 1999
}





razorpay_client = razorpay.Client(auth=("rzp_test_RHZzbN9mv0IB2i", "i8KVpmeVT6FmOMLdyQCcKx79"))

app = Flask(__name__)
app.secret_key = "your_secret_key"

# MySQL connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="xxxx",
    database="xxxx"
)
cursor = db.cursor(dictionary=True)

# ---------- Image Upload Folders ----------
UPLOAD_FOLDER = "static/uploads"
RESULT_FOLDER = "static/results"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/index')
def login_page():
    return render_template('index.html')

@app.route('/index')
def index_page():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT testimony FROM testimonies ORDER BY created_at DESC LIMIT 5")
    testimonies = cursor.fetchall()
    cursor.close()
    return render_template('index.html', testimonies=testimonies)

#@app.route("/testimonials")
#def testimonials():
#    cursor.execute("""
 #       SELECT testimonies.id, testimonies.testimony, testimonies.created_at, users.name
 #       FROM testimonies
 #       JOIN users ON testimonies.user_id = users.id
 #       ORDER BY testimonies.created_at DESC
 #   """)
 #   testimonials = cursor.fetchall()   # list of dicts
 #   return render_template("testimonials.html", testimonials=testimonials)

@app.route("/testimonials")
def testimonials():
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT t.testimony, t.created_at, u.name
        FROM testimonies t
        JOIN users u ON t.user_id = u.id
        ORDER BY t.created_at DESC
    """)
    testimonials = cursor.fetchall()
    cursor.close()
    return render_template("testimonials.html", testimonials=testimonials)




@app.route('/main')
def main():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('main.html')

# Signup route
@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = generate_password_hash(request.form['password'])
    
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    if user:
        flash("Email already registered!", "error")
        return redirect(url_for('index'))
    
    cursor.execute("INSERT INTO users (name, email, password) VALUES (%s,%s,%s)", (name, email, password))
    db.commit()
    flash("Account created successfully!", "success")
    return redirect(url_for('index'))

# Login route
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    
    cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()
    
    #if user and check_password_hash(user['password'], password):
     #   session['user_id'] = user['id']
      #  flash(f"Welcome {user['name']}!", "success")
      #  return redirect(url_for('main'))
    if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            flash(f"Welcome {user['name']}!", "success")
            return redirect(url_for('main'))

    else:
        flash("Invalid email or password!", "error")
        return redirect(url_for('index'))

# ---------- Upload Page ----------
@app.route('/upload')
def upload_page():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('upload.html')

# ---------- Cartoonize Process ----------
@app.route('/cartoonize', methods=['POST'])
def cartoonize():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    if 'image' not in request.files:
        flash("No file uploaded!", "error")
        return redirect(url_for('upload_page'))

    file = request.files['image']
    style = request.form.get("style")
    if file.filename == '':
        flash("No selected file!", "error")
        return redirect(url_for('upload_page'))

    # Save uploaded image
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    # Process depending on style
    if style == "opencv":
        cartoon = cartoonize_image(file_path)
        output_path = os.path.join(RESULT_FOLDER, "opencv_" + file.filename)
        cv2.imwrite(output_path, cartoon)

    elif style == "sketch":
        gray = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
        inv = 255 - gray
        blur = cv2.GaussianBlur(inv, (21,21), 0)
        sketch = cv2.divide(gray, 255-blur, scale=256)
        output_path = os.path.join(RESULT_FOLDER, "sketch_" + file.filename)
        cv2.imwrite(output_path, sketch)

    elif style in ["anime_facepaint_v2", "anime_facepaint_v1","anime_paprika", "anime_celeba"]:
        output_path = os.path.join(RESULT_FOLDER, style + "_" + file.filename)
        style_weights = {
            "anime_facepaint_v1": "face_paint_512_v1",
            "anime_facepaint_v2": "face_paint_512_v2",
            "anime_paprika": "paprika",
            "anime_celeba": "celeba_distill"
        }
        animegan_cartoonize(file_path, output_path, style_weights[style])

    elif style == "ghibli":
        output_path = os.path.join(RESULT_FOLDER, "ghibli_" + file.filename)
        ghibli_cartoonize(file_path, output_path)

    elif style == "whitebox":
        output_path = os.path.join(RESULT_FOLDER, "whitebox_" + file.filename)

    # Save paths in DB
    cursor.execute(
        "INSERT INTO images (user_id, original_path, cartoon_path) VALUES (%s, %s, %s)",
        (session['user_id'], file_path, output_path)
    )
    db.commit()
    image_id = cursor.lastrowid  # ✅ get inserted image id

    return render_template("result.html",
                           original_image=file_path,
                           cartoon_image=output_path,
                           image_id=image_id)   # ✅ pass id

@app.route("/choose_download")
def choose_download():
    if "user_id" not in session:
        return redirect(url_for("index"))

    cartoon_image = request.args.get("cartoon_image")
    original_image = request.args.get("original_image")
    image_id = request.args.get("image_id")   # ✅ fetch id

    # 🔹 Check active subscription
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM subscriptions 
        WHERE user_id = %s AND status = 'success'
        AND (end_date IS NULL OR end_date > NOW())
        LIMIT 1
    """, (session["user_id"],))
    active_subscription = cursor.fetchone()
    cursor.close()

    return render_template("choose_download.html",
                           cartoon_image=cartoon_image,
                           original_image=original_image,
                           image_id=image_id,
                           active_subscription=active_subscription)




@app.route("/download_free")
def download_free():
    if "user_id" not in session:
        return redirect(url_for("index"))

    cartoon_image = request.args.get("cartoon_image")
    if not cartoon_image:
        return "No image provided", 400

    image_path = cartoon_image  
    image = cv2.imread(image_path)
    if image is None:
        return f"Image not found at {image_path}", 404

    # Add diagonal watermark
    overlay = image.copy()
    output = image.copy()
    watermark_text = "Cartoonify AI"
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 3
    thickness = 8
    color = (0,0,255)

    (h, w) = image.shape[:2]
    text_size = cv2.getTextSize(watermark_text, font, font_scale, thickness)[0]
    text_x = (w - text_size[0]) // 2
    text_y = (h + text_size[1]) // 2

    cv2.putText(overlay, watermark_text, (text_x, text_y), font,
                font_scale, color, thickness, cv2.LINE_AA)
    M = cv2.getRotationMatrix2D((w//2, h//2), -50, 1)
    rotated_overlay = cv2.warpAffine(overlay, M, (w, h))
    cv2.addWeighted(rotated_overlay, 0.3, output, 0.7, 0, output)

    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    cv2.imwrite(tmp_file.name, output)

    return send_file(tmp_file.name, as_attachment=True, download_name="cartoon_with_watermark.jpg")


@app.route("/game_unlock/<int:image_id>")
def game_unlock(image_id):
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = session["user_id"]
    today = date.today()

    cursor.execute("SELECT * FROM usage_log WHERE user_id=%s AND usage_date=%s", (user_id, today))
    record = cursor.fetchone()

    if record and record["trial_count"] >= 5:
        # Show a special page (no game, only alert)
        return render_template("game_limit.html",
                               error="⚠️ You have reached your daily limit of 5 unlocked downloads. Please try again tomorrow.")

    # ✅ Only show game if not blocked
    return render_template("game.html", image_id=image_id)







@app.route("/download_image_unlocked/<int:image_id>")
def download_image_unlocked(image_id):
    if "user_id" not in session:
        return redirect(url_for("index"))

    user_id = session["user_id"]
    today = date.today()

    # Check if usage record exists for today
    cursor.execute("SELECT * FROM usage_log WHERE user_id=%s AND usage_date=%s", (user_id, today))
    record = cursor.fetchone()

    if record and record["trial_count"] >= 5:
        flash("You have reached your daily limit of 5 unlocked downloads. Please try again tomorrow.", "danger")
        return redirect(url_for("my_images"))

    # ✅ Fetch cartoon path
    cursor.execute("SELECT cartoon_path FROM images WHERE id=%s AND user_id=%s", (image_id, user_id))
    img = cursor.fetchone()

    if img:
        # Update usage_log
        if record:
            cursor.execute("UPDATE usage_log SET trial_count = trial_count + 1 WHERE id = %s", (record["id"],))
        else:
            cursor.execute("INSERT INTO usage_log (user_id, usage_date, trial_count) VALUES (%s, %s, %s)", 
                           (user_id, today, 1))
        db.commit()

        return send_file(img["cartoon_path"], as_attachment=True)

    flash("Image not found", "danger")
    return redirect(url_for("my_images"))


# ---------- other routes (profile, update, logout, etc.) ----------
# keep your existing code here unchanged ...
# Profile page
#@app.route('/profile')
#def profile():
#    if 'user_id' not in session:
#        return redirect(url_for('index'))
#    
#    cursor.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
#    user = cursor.fetchone()
#    return render_template('profile.html', user=user)
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    cursor = db.cursor(dictionary=True)

    # Fetch user details
    cursor.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()

    # Fetch latest subscription for this user
    cursor.execute("""
        SELECT package_name, start_date, end_date,
        CASE 
            WHEN end_date >= CURDATE() THEN 'Active'
            ELSE 'Expired'
        END AS status
        FROM subscriptions
        WHERE user_id = %s
        ORDER BY end_date DESC
        LIMIT 1
    """, (session['user_id'],))
    subscription = cursor.fetchone()

    cursor.close()

    return render_template('profile.html', user=user, subscription=subscription)


# ---------- Update Name ----------
@app.route("/update_name", methods=["POST"])
def update_name():
    if "user_id" not in session:
        return redirect(url_for("index"))

    new_name = request.form["name"]
    cursor.execute("UPDATE users SET name=%s WHERE id=%s", (new_name, session["user_id"]))
    db.commit()

    flash("Name updated successfully!", "success")
    return redirect(url_for("profile"))

# ---------- Update Email ----------
@app.route("/update_email", methods=["POST"])
def update_email():
    if "user_id" not in session:
        return redirect(url_for("index"))

    new_email = request.form["email"]
    cursor.execute("UPDATE users SET email=%s WHERE id=%s", (new_email, session["user_id"]))
    db.commit()

    flash("Email updated successfully!", "success")
    return redirect(url_for("profile"))

# ---------- Update Password ----------
@app.route("/update_password", methods=["POST"])
def update_password():
    if "user_id" not in session:
        return redirect(url_for("index"))

    old_password = request.form["old_password"]
    new_password = request.form["new_password"]

    cursor.execute("SELECT password FROM users WHERE id=%s", (session["user_id"],))
    user = cursor.fetchone()

    if not check_password_hash(user["password"], old_password):
        flash("Old password is incorrect!", "error")
        return redirect(url_for("profile"))

    hashed_password = generate_password_hash(new_password)
    cursor.execute("UPDATE users SET password=%s WHERE id=%s", (hashed_password, session["user_id"]))
    db.commit()

    flash("Password updated successfully!", "success")
    return redirect(url_for("profile"))

# ---------- Delete Account ----------
@app.route("/delete_account", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        return redirect(url_for("index"))

    cursor.execute("DELETE FROM users WHERE id=%s", (session["user_id"],))
    db.commit()
    session.clear()

    flash("Your account has been deleted.", "info")
    return redirect(url_for("index"))

# ---------- Logout ----------
@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/my_images")
def my_images():
    if "user_id" not in session:
        flash("Please log in first", "danger")
        return redirect(url_for("index"))

    user_id = session["user_id"]

    cursor.execute("SELECT * FROM images WHERE user_id = %s ORDER BY uploaded_at DESC", (user_id,))
    images = cursor.fetchall()

    return render_template("my_images.html", images=images)






@app.route("/delete_image/<int:image_id>")
def delete_image(image_id):
    if "user_id" not in session:
        return redirect(url_for("index"))

    # Fetch paths before deleting
    cursor.execute("SELECT original_path, cartoon_path FROM images WHERE id=%s AND user_id=%s",
                   (image_id, session["user_id"]))
    img = cursor.fetchone()

    if img:
        # Delete from DB
        cursor.execute("DELETE FROM images WHERE id = %s AND user_id = %s", (image_id, session["user_id"]))
        db.commit()

        # Delete files from disk if they exist
        for path in [img["original_path"], img["cartoon_path"]]:
            if os.path.exists(path):
                os.remove(path)

        flash("Image and record deleted successfully", "success")
    else:
        flash("Image not found", "danger")

    return redirect(url_for("my_images"))



@app.route("/download_image/<int:image_id>")
def download_image(image_id):
    if "user_id" not in session:
        return redirect(url_for("index"))

    cursor.execute("SELECT cartoon_path FROM images WHERE id = %s AND user_id = %s", (image_id, session["user_id"]))
    img = cursor.fetchone()

    if img:
        return send_file(img["cartoon_path"], as_attachment=True)

    flash("Image not found", "danger")
    return redirect(url_for("my_images"))

@app.route("/subscription")
def subscription():
    if "user_id" not in session:
        return redirect(url_for("index"))
    return render_template("subscription.html")

#@app.route("/subscribe")
#def subscribe():
    # This will render your subscription packages page
#    return render_template("subscribe.html")

# Show subscription page
#@app.route("/subscribe")
#def show_subscribe():
 #   return render_template("subscription.html")


# Handle subscription form
#@app.route('/subscribe', methods=['POST'])
#def subscribe():
 #   if 'user_id' not in session:
  #      flash("Please login to subscribe")
   #     return redirect(url_for('login'))

    #plan = request.form['plan']
   # duration = request.form['duration']
    #user_id = session['user_id']

    #cursor = db.cursor()
    #cursor.execute(
     #   "INSERT INTO subscriptions (user_id, package_name, duration, start_date, end_date) VALUES (%s, %s, %s, CURDATE(), DATE_ADD(CURDATE(), INTERVAL %s MONTH))",
      #  (user_id, plan, duration, duration)
    #)
    #db.commit()
    #cursor.close()

    #flash(f"You have successfully subscribed to the {plan} plan!")
    #return redirect(url_for('dashboard'))



@app.route('/subscribe', methods=['POST'])
def subscribe():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    plan = request.form.get('plan')  # From subscribe.html form
    

    if plan not in PRICES:
        flash("Invalid plan selected", "danger")
        return redirect(url_for('show_subscribe'))

    cursor = db.cursor(dictionary=True)

    if plan == "Basic":
        credits = 1
        cursor.execute("INSERT INTO user_credits (user_id, credits) VALUES (%s, %s) "
                       "ON DUPLICATE KEY UPDATE credits = credits + %s",
                       (session['user_id'], credits, credits))
        db.commit()
        flash("✅ Basic plan activated: 1 credit added", "success")

    elif plan == "Standard":
        credits = 30
        cursor.execute("INSERT INTO user_credits (user_id, credits) VALUES (%s, %s) "
                       "ON DUPLICATE KEY UPDATE credits = credits + %s",
                       (session['user_id'], credits, credits))
        db.commit()
        flash("✅ Standard plan activated: 30 credits added", "success")

    elif plan == "Pro":
        start_date = datetime.now()
        end_date = start_date + timedelta(days=365)
        cursor.execute("""INSERT INTO subscriptions (user_id, package_name, amount, status, start_date, end_date)
                          VALUES (%s, %s, %s, 'success', %s, %s)""",
                       (session['user_id'], plan, PRICES[plan], start_date, end_date))
        db.commit()
        flash("✅ Pro plan activated for 1 year", "success")

    elif plan == "Premium":
        start_date = datetime.now()
        cursor.execute("""INSERT INTO subscriptions (user_id, package_name, amount, status, start_date, end_date)
                          VALUES (%s, %s, %s, 'success', %s, NULL)""",
                       (session['user_id'], plan, PRICES[plan], start_date))
        db.commit()
        flash("✅ Premium plan activated: Lifetime access", "success")

    cursor.close()
    return redirect(url_for('profile'))



#@app.route("/proceed_to_pay/<package>")
#def proceed_to_pay(package):
#    if "user_id" not in session:
#        return redirect(url_for("login"))  # make sure user logged in

 #   user_id = session["user_id"]

    # Define package prices
#    prices = {
 #       "Basic": 49,
  #      "Standard": 99,
  #      "Pro": 199,
 #       "Premium": 299
   # }

  #  amount = prices.get(package, 0)

    # Insert subscription (status pending)
   # cursor.execute("""
    #    INSERT INTO subscriptions (user_id, package_name, amount, status, start_date, end_date)
     #   VALUES (%s, %s, %s, %s, %s, %s)
   # """, (user_id, package, amount, "pending", datetime.now(), datetime.now() + timedelta(days=30)))
   # db.commit()

    # Temporary success message (until we add payment gateway)
    #return f"✅ Subscription for {package} plan created successfully!"

@app.route("/create_order/<package>")
def create_order(package):
    if "user_id" not in session:
        return redirect(url_for("index"))

    if package not in PRICES:
        flash("Invalid package", "danger")
        return redirect(url_for('subscription'))

    user_id = session["user_id"]
    cursor = db.cursor(dictionary=True)

    # Check if user already has active subscription
    cursor.execute("""
      SELECT * FROM subscriptions
      WHERE user_id=%s AND status='success' AND (end_date IS NULL OR end_date >= CURDATE())
    """, (user_id,))
    active = cursor.fetchone()
    if active:
        flash(f"You already have an active subscription until {active['end_date']}", "info")
        cursor.close()
        return redirect(url_for('profile'))

    amount = PRICES[package] * 100  # in paise

    # create Razorpay order
    order = razorpay_client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": "1"
    })

    # Calculate end_date based on package
    start_date = datetime.now()
    if package == "Basic":
        end_date = start_date + timedelta(days=1)
    elif package == "Standard":
        end_date = start_date + timedelta(days=30)
    elif package == "Pro":
        end_date = start_date + timedelta(days=365)
    elif package == "Premium":
        end_date = datetime(9999, 12, 31)  # lifetime
    else:
        end_date = start_date + timedelta(days=30)

    # Insert pending subscription
    cursor.execute("""
      INSERT INTO subscriptions 
      (user_id, package_name, amount, status, start_date, end_date, razorpay_order_id)
      VALUES (%s, %s, %s, 'pending', %s, %s, %s)
    """, (user_id, package, PRICES[package], start_date, end_date, order['id']))
    db.commit()
    cursor.close()

    return render_template("checkout.html", package=package, amount=amount, order=order)






@app.route("/payment_success", methods=["POST"])
def payment_success():
    package = request.form.get("package")
    user_id = session.get("user_id")

    if not user_id:
        flash("Session expired. Please login again.", "danger")
        return redirect(url_for("index"))

    razorpay_payment_id = request.form.get("razorpay_payment_id")
    razorpay_order_id = request.form.get("razorpay_order_id")
    razorpay_signature = request.form.get("razorpay_signature")

    # Verify signature
    try:
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
    except SignatureVerificationError:
        flash("Payment verification failed. Please contact support.", "danger")
        return redirect(url_for('subscription'))

    cursor = db.cursor(dictionary=True)

    # Find pending subscription
    cursor.execute("""
      SELECT * FROM subscriptions
      WHERE user_id=%s AND razorpay_order_id=%s AND status='pending'
      ORDER BY start_date DESC LIMIT 1
    """, (user_id, razorpay_order_id))
    pending = cursor.fetchone()

    if not pending:
        flash("Pending subscription not found. Contact support.", "danger")
        cursor.close()
        return redirect(url_for("subscription"))

    # Update subscription to success
    cursor.execute("""
      UPDATE subscriptions
      SET status='success',
          razorpay_payment_id=%s,
          razorpay_signature=%s
      WHERE id=%s
    """, (razorpay_payment_id, razorpay_signature, pending['id']))
    db.commit()
    cursor.close()

    # Store a one-time success flag in session
    session['payment_status'] = "success"
    return redirect(url_for("payment_result"))

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response



@app.route("/payment_result")
def payment_result():
    status = session.pop("payment_status", None)
    if status == "success":
        flash("✅ Payment successful! Subscription activated.", "success")
    return redirect(url_for("profile"))



@app.route("/subscribe_temp/<plan>")
def subscribe_temp(plan):
    if "user_id" not in session:
        flash("Please login first", "danger")
        return redirect(url_for("index"))

    if plan not in PRICES:
        flash("Invalid plan selected", "danger")
        return redirect(url_for("subscription"))

    user_id = session["user_id"]
    cursor = db.cursor(dictionary=True)

    start_date = datetime.now()
    if plan == "Basic":
        end_date = start_date + timedelta(days=1)
    elif plan == "Standard":
        end_date = start_date + timedelta(days=30)
    elif plan == "Pro":
        end_date = start_date + timedelta(days=365)
    elif plan == "Premium":
        end_date = datetime(9999, 12, 31)
    else:
        end_date = start_date + timedelta(days=30)

    # Insert subscription as success immediately
    cursor.execute("""
        INSERT INTO subscriptions (user_id, package_name, amount, status, start_date, end_date)
        VALUES (%s, %s, %s, 'success', %s, %s)
    """, (user_id, plan, PRICES[plan], start_date, end_date))
    db.commit()
    cursor.close()

    flash(f"✅ Temporary {plan} subscription activated!", "success")
    # redirect back to choose_download page or profile
    return redirect(url_for("profile"))






@app.route('/download_subscribed')
def download_subscribed():
    if "user_id" not in session:
        return redirect(url_for("index"))

    cartoon_image = request.args.get("cartoon_image")

    # ✅ Ensure user has active subscription
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM subscriptions 
        WHERE user_id = %s AND status = 'success' 
        AND (end_date IS NULL OR end_date > NOW())
        LIMIT 1
    """, (session['user_id'],))
    active_subscription = cursor.fetchone()
    cursor.close()

    if not active_subscription:
        flash("❌ You need a subscription to download without watermark", "danger")
        return redirect(url_for('choose_download'))

    # If subscribed → allow direct download
    return send_file(cartoon_image, as_attachment=True, download_name="cartoon_hd.png")





@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM admins WHERE email=%s AND password=%s", (email, password))
        admin = cursor.fetchone()

        if admin:
            session["admin_id"] = admin["id"]
            session["role"] = admin["role"]
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid admin credentials")
            return redirect(url_for("admin_login"))

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():
    cursor = db.cursor(dictionary=True)

    # Total users
    cursor.execute("SELECT COUNT(*) AS total_users FROM users")
    total_users = cursor.fetchone()["total_users"]

    # Total images
    cursor.execute("SELECT COUNT(*) AS total_images FROM images")
    total_images = cursor.fetchone()["total_images"]

    # Active subscriptions
    cursor.execute("""
        SELECT COUNT(*) AS active_subscriptions
        FROM subscriptions
        WHERE status='success' AND (end_date IS NULL OR end_date > NOW())
    """)
    active_subscriptions = cursor.fetchone()["active_subscriptions"]

    # Total admins
    cursor.execute("SELECT COUNT(*) AS total_admins FROM admins")
    total_admins = cursor.fetchone()["total_admins"]

    # Users table
    cursor.execute("""
        SELECT 
            u.id,
            u.name,
            u.email,
            COALESCE(s.status, 'No Subscription') AS subscription_status,
            COUNT(i.id) AS images_created
        FROM users u
        LEFT JOIN (
            SELECT s1.* 
            FROM subscriptions s1
            WHERE s1.id = (
                SELECT s2.id FROM subscriptions s2
                WHERE s2.user_id = s1.user_id
                ORDER BY s2.start_date DESC LIMIT 1
            )
        ) s ON u.id = s.user_id
        LEFT JOIN images i ON u.id = i.user_id
        GROUP BY u.id, u.name, u.email, s.status
        ORDER BY u.id
    """)
    users = cursor.fetchall()

    # ---------- Chart 1: Images per user ----------
    cursor.execute("""
        SELECT u.name, COUNT(i.id) AS image_count
        FROM users u
        LEFT JOIN images i ON u.id = i.user_id
        GROUP BY u.id
    """)
    chart_data = cursor.fetchall()
    user_names = [row['name'] for row in chart_data]
    image_counts = [row['image_count'] for row in chart_data]

    # ---------- Chart 2: Daily image uploads (last 7 days) ----------
    cursor.execute("""
        SELECT DATE(uploaded_at) AS upload_date, COUNT(*) AS daily_count
        FROM images
        WHERE uploaded_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
        GROUP BY DATE(uploaded_at)
        ORDER BY upload_date
    """)
    daily_data = cursor.fetchall()
    daily_labels = [row['upload_date'].strftime('%Y-%m-%d') for row in daily_data]
    daily_counts = [row['daily_count'] for row in daily_data]

    cursor.close()

    return render_template(
        "admin_dashboard.html",
        total_users=total_users,
        total_images=total_images,
        active_subscriptions=active_subscriptions,
        total_admins=total_admins,
        users=users,
        user_names=user_names,       # Images per user chart
        image_counts=image_counts,   # Images per user chart
        daily_labels=daily_labels,   # Daily uploads chart
        daily_counts=daily_counts    # Daily uploads chart
    )





@app.route("/admin/settings")
def admin_settings():
    if "user_id" not in session:
        return redirect(url_for("index"))
    return render_template("admin_settings.html")




@app.route("/add_admin", methods=["POST"])
def add_admin():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]



    # Check if admin exists
    cursor.execute("SELECT * FROM admins WHERE email=%s", (email,))
    existing = cursor.fetchone()
    if existing:
        flash("❌ Email already registered as admin", "danger")
        return redirect(url_for("admin_settings"))

    # Insert new admin
    cursor.execute("INSERT INTO admins (name, email, password) VALUES (%s, %s, %s)",
                   (name, email, password))
    db.commit()
    flash("✅ New admin added successfully!", "success")
    return redirect(url_for("admin_settings"))


@app.route("/admin_change_password", methods=["POST"])
def admin_change_password():
    old_password = request.form.get("old_password")
    new_password = request.form.get("new_password")
    user_id = int(session.get("user_id"))

    cursor.execute("SELECT password FROM admins WHERE id=%s", (user_id,))
    admin = cursor.fetchone()

    if not admin:
        flash("❌ Admin not found", "danger")
        return redirect(url_for("admin_settings"))

    if old_password != admin[0]:
        flash("❌ Old password is incorrect", "danger")
        return redirect(url_for("admin_settings"))

    cursor.execute("UPDATE admins SET password=%s WHERE id=%s", (new_password, user_id))
    db.commit()

    if cursor.rowcount == 0:
        flash("❌ Password update failed", "danger")
    else:
        flash("✅ Password updated successfully", "success")

    return redirect(url_for("admin_settings"))

# View all testimonies of logged-in user
@app.route('/testimonies')
def testimonies():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM testimonies WHERE user_id=%s ORDER BY created_at DESC", (session['user_id'],))
    testimonies = cursor.fetchall()
    cursor.close()

    # For now, just store in DB and show as simple flash or redirect
    # You can also return JSON for testing
    return {"testimonies": testimonies}  # temporary: returns JSON instead of rendering template




# Add new testimony (store only in DB)
@app.route('/add_testimony', methods=['POST'])
def add_testimony():
    if 'user_id' not in session:
        return redirect(url_for('index'))

    new_testimony = request.form['new_testimony']
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO testimonies (user_id, testimony) VALUES (%s, %s)",
        (session['user_id'], new_testimony)
    )
    db.commit()
    cursor.close()
    
    flash("Testimony stored successfully!", "success")
    return redirect(url_for('profile'))  # or redirect wherever you want



# Update existing testimony
@app.route('/update_testimony/<int:testimony_id>', methods=['POST'])
def update_testimony(testimony_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))

    new_text = request.form['new_testimony']
    cursor = db.cursor()
    cursor.execute("UPDATE testimonies SET testimony=%s WHERE id=%s AND user_id=%s", 
                   (new_text, testimony_id, session['user_id']))
    db.commit()
    cursor.close()
    flash("Testimony updated!", "success")
    return redirect(url_for('testimonies'))









    







if __name__ == '__main__':
    app.run(debug=True)
