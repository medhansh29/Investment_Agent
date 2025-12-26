# **Project: Hybrid AI Investment Agent (User-Centric Edition)**

### **Core Logic**

1. **The Math (PyPortfolioOpt)**: Calculates the hard numbers (Allocation & Risk).  
2. **The AI (Gemini)**: Translates math into plain English and checks market timing (The "Advisor").  
3. **The Hands (Alpaca)**: Fetches data efficiently and executes the trades.

---

### **Step 1: User Input & Profile**

**Action:** Initialize session constraints.

**Internal State JSON:**

{  
  "user\_info": {  
    "name": "Alex",  
    "age": 30,  
    "email": "alex@example.com"  
  },  
  "strategy\_settings": {  
    "risk\_profile": "high\_growth",  
    "monthly\_investment": 500.00,  
    "lookback\_years": 3,  
    "universe": \["AAPL", "MSFT", "GOOG", "TSLA", "NVDA", "KO"\]  
  },  
  "last\_run": "2023-10-27"  
}

---

### **Step 2: Optimized Data Fetching (Alpaca)**

**Action:** Fetch 3 years of data using **"Chunking"** (batches of 10\) to prevent timeouts.

**Python Logic (Conceptual):**

Python  
\# Instead of 50 individual calls, we do 5 batches of 10\.  
\# Time: \~4 seconds total.  
batches \= \[universe\[i:i \+ 10\] for i in range(0, len(universe), 10)\]  
for batch in batches:  
    alpaca.get\_bars(batch, timeframe='1Day', start='2021-01-01')

---

### **Step 3: The "Two-Brain" Analysis**

#### **3A. The Math (PyPortfolioOpt)**

**Action:** Compare "Current Portfolio" vs. "Efficient Frontier" to find the difference.

**Internal Calculation Output (The "Diff"):**

JSON  
{  
  "AAPL": {"action": "SELL", "diff": \-5},  // We have 5 too many  
  "MSFT": {"action": "BUY",  "diff": \+10}, // We need 10 more  
  "KO":   {"action": "HOLD", "diff": 0}    // Balanced  
}

#### **3B. The AI Advisor (Gemini API)**

**Action:** Translate the Math's "Diff" into a friendly user report, checking trends for timing.

**Prompt Input (Sent to Gemini):**

Plaintext  
Role: You are a friendly financial advisor.  
Input Data:  
1\. Math says SELL 5 AAPL. (Reason: Overweight). Trend: Bearish.  
2\. Math says BUY 10 MSFT. (Reason: Diversify). Trend: Stable.  
3\. Math says HOLD KO. (Reason: Balanced).

Task: Create a JSON report explaining this simply to a beginner.  
Classify into "Action Required" and "No Action Needed".

**Gemini Output (JSON):**

JSON  
{  
  "action\_required": {  
    "sells": \[  
      {  
        "ticker": "AAPL",  
        "amount": 5,  
        "why": "You have made a good profit here, but you own too much of it now. Let's sell 5 shares to reduce your risk."  
      }  
    \],  
    "buys": \[  
      {  
        "ticker": "MSFT",  
        "amount": 10,  
        "why": "This is a strong company that adds balance to your portfolio. It is currently at a fair price to enter."  
      }  
    \]  
  },  
  "no\_action\_needed": {  
    "holds": \[  
      {  
        "ticker": "KO",  
        "amount": 50,  
        "why": "This is your safety net. It is doing exactly what it should—providing stability. No need to touch it."  
      }  
    \]  
  }  
}

---

### **Step 4: User Review & Execution**

**Action:** Display the "Simple English" report. Wait for `Y` confirmation.

