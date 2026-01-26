# OptiClaimAI - SaaS Edition Setup Guide

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in project root:

```env
# Database
DATABASE_URL=sqlite:///opticlaimai.db

# Stripe Keys (get from https://dashboard.stripe.com)
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxx
STRIPE_PUBLIC_KEY=pk_test_xxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxx
STRIPE_ENDPOINT_SECRET=whsec_xxxxxxxxxxxx

# Stripe Product Prices (create in Stripe Dashboard)
STRIPE_PRICE_BASIC=price_xxxxxxxxxxxx    # $49/month
STRIPE_PRICE_PRO=price_xxxxxxxxxxxx      # $149/month

# AI Configuration
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2
OPENAI_API_KEY=sk-xxxxxxxxxxxx           # Optional

# Deployment
APP_URL=https://opticlaimai.com           # For production
DEBUG=false
```

### 3. Initialize Database

```bash
python -c "from services.database import init_db; init_db()"
```

### 4. Run the App

```bash
python -m streamlit run streamlit_app_saas.py
```

Access at: `http://localhost:8501`

---

## 💳 Stripe Setup (CRITICAL)

### Step 1: Create Stripe Account
1. Go to https://stripe.com
2. Sign up for free account
3. Get to Dashboard

### Step 2: Create Products & Prices
1. Go to Products → Create Product
2. Create "OptiClaimAI - Basic"
   - Price: $49/month
   - Billing period: Monthly
   - Copy price ID to `.env` as `STRIPE_PRICE_BASIC`

3. Create "OptiClaimAI - Pro"
   - Price: $149/month
   - Billing period: Monthly
   - Copy price ID to `.env` as `STRIPE_PRICE_PRO`

### Step 3: Get API Keys
1. Go to Developers → API Keys
2. Copy Secret Key → `STRIPE_SECRET_KEY` in `.env`
3. Copy Publishable Key → `STRIPE_PUBLIC_KEY` in `.env`

### Step 4: Set Up Webhooks
1. Go to Developers → Webhooks
2. Click "Add endpoint"
3. URL: `https://yourdomain.com/webhook`
4. Events to listen for:
   - checkout.session.completed
   - customer.subscription.updated
   - customer.subscription.deleted
   - invoice.payment_failed

5. Copy signing secret → `STRIPE_WEBHOOK_SECRET` and `STRIPE_ENDPOINT_SECRET`

---

## 🔐 Payment Gating (HOW IT WORKS)

### Authentication Flow
```
User → Register/Login → Redirected to billing if inactive → Stripe Checkout
```

### Subscription Verification
Every feature checks `require_active_subscription()`:
```python
def require_active_subscription():
    is_active = AuthService.verify_subscription_active(user_id)
    if not is_active:
        show_upgrade_prompt()
        st.stop()  # Blocks feature execution
```

### Usage Limits
Each action checks `check_usage_limit()`:
```python
is_allowed, message = check_usage_limit(user_id, "claim_created")
if not is_allowed:
    st.error(message)  # Block execution
    st.stop()
```

### Feature Gating
AI and premium features check `require_feature()`:
```python
if not require_feature("ai_full"):
    st.error("Upgrade to Pro")
    st.stop()
```

---

## 📊 Database Schema

### Users Table
- id (PK)
- email (unique)
- password_hash (bcrypt)
- first_name, last_name
- created_at, updated_at
- is_active

### Subscriptions Table
- id (PK)
- user_id (FK, unique)
- tier (basic, pro, enterprise)
- stripe_customer_id, stripe_subscription_id
- status (active, past_due, canceled)
- current_period_start, current_period_end

### UsageLogs Table
- id (PK)
- user_id (FK)
- action (claim_created, claim_validated, edi_generated, ai_called)
- count
- timestamp

### Claims Table
- id (PK)
- user_id (FK)
- claim_id (unique)
- encrypted_data (AES-256)
- status (pending, validated, exported)
- created_at, updated_at

---

## 🧪 Testing End-to-End

### Test User Flow

1. **Register Account**
   ```
   Email: test@example.com
   Password: TestPassword123
   ```

2. **See Billing Prompt**
   - App shows "Subscription inactive"
   - Click "Upgrade to Pro"

3. **Stripe Checkout**
   - Use test card: `4242 4242 4242 4242`
   - Expiry: `12/25`
   - CVC: `123`
   - Complete payment

4. **Access Features**
   - Create claim → ✅ Works
   - Validate claim → ✅ Works
   - Use AI → ✅ Works (Pro only)
   - Export EDI → ✅ Works

5. **Test Usage Limits**
   - Create 10 claims (BASIC limit)
   - 11th claim blocked: "Monthly limit exceeded"

6. **Upgrade to Pro**
   - Click "Upgrade" button
   - Complete Stripe checkout for Pro tier
   - Limits removed → Unlimited claims

---

## 🔄 Webhook Handling

### Local Testing with ngrok

```bash
# Install ngrok
pip install ngrok

# Start ngrok tunnel
ngrok http 8501

# Add webhook endpoint (URL = ngrok URL + /webhook)
```

### Webhook Events Handled
- `checkout.session.completed` → Create subscription
- `customer.subscription.updated` → Update subscription status
- `customer.subscription.deleted` → Mark subscription canceled
- `invoice.payment_failed` → Mark subscription past_due

---

## 📧 Email Notifications (TODO)

When implemented, send:
- Payment failed notification
- Subscription renewal reminder
- Upgrade upsell email

---

## 🛡️ Security Checklist

- ✅ Passwords hashed with bcrypt
- ✅ SQL injection prevented (SQLAlchemy ORM)
- ✅ Claims encrypted in database (TODO: implement)
- ✅ API keys in environment variables
- ✅ HTTPS required for production
- ✅ Stripe secrets never logged
- ⚠️ TODO: Implement rate limiting
- ⚠️ TODO: Add CSRF protection

---

## 🚢 Production Deployment

### Option 1: Heroku

```bash
# Create Procfile
echo "web: streamlit run streamlit_app_saas.py" > Procfile

# Deploy
heroku create opticlaimai
heroku config:set DATABASE_URL=postgresql://...
heroku config:set STRIPE_SECRET_KEY=sk_live_...
git push heroku main
```

### Option 2: AWS Lambda + API Gateway

Use serverless framework to deploy Streamlit backend with FastAPI gateway.

### Option 3: Docker

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV DATABASE_URL=postgresql://...
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app_saas.py"]
```

---

## 📞 Support

- Issues: support@opticlaimai.com
- Stripe Support: https://support.stripe.com
- Streamlit Docs: https://docs.streamlit.io

---

**Last Updated:** January 25, 2026  
**Status:** Ready for SaaS Testing
