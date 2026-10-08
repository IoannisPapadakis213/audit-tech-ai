import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_gl_data(num_records=10000):
    np.random.seed(42)
    
    # 1. Βασικές παράμετροι
    accounts = ['Revenue', 'Payroll', 'Office Supplies', 'Marketing', 'Consulting Fees', 'Travel']
    users = ['User_01', 'User_02', 'User_03', 'User_04', 'System_Auto']
    
    # 2. Γεννήτρια τυχαίων ημερομηνιών για το 2023
    start_date = datetime(2023, 1, 1)
    dates = [start_date + timedelta(days=int(np.random.randint(0, 365))) for _ in range(num_records)]
    
    # 3. Δημιουργία του βασικού πίνακα (DataFrame)
    df = pd.DataFrame({
        'transaction_id': [f"TRX-{100000 + i}" for i in range(num_records)],
        'date': dates,
        'account': np.random.choice(accounts, num_records),
        'amount': np.round(np.random.uniform(50, 5000, num_records), 2),
        'user_id': np.random.choice(users, num_records),
        'description': 'Standard entry'
    })
    
    # --- 4. ΕΙΣΑΓΩΓΗ "ΑΝΩΜΑΛΙΩΝ" ΓΙΑ ΝΑ ΒΡΕΙ ΤΟ AI ΜΑΣ ΑΡΓΟΤΕΡΑ ---
    
    # Ανωμαλία Α: Στρογγυλά, τεράστια ποσά (συχνό red flag για απάτη)
    round_indices = np.random.choice(df.index, 50, replace=False)
    df.loc[round_indices, 'amount'] = np.random.choice([10000.00, 25000.00, 50000.00], 50)
    df.loc[round_indices, 'description'] = 'Consulting advance payment'
    
    # Ανωμαλία Β: Εγγραφές Σαββατοκύριακου (σπάνιο στην πραγματική λογιστική)
    df['is_weekend'] = df['date'].dt.weekday >= 5
    weekend_indices = df[df['is_weekend']].sample(30).index
    df.loc[weekend_indices, 'user_id'] = 'User_04' # Ο User_04 είναι ο... ύποπτος
    df.loc[weekend_indices, 'description'] = 'Urgent weekend adjustment'
    
    # Αφαιρούμε τη στήλη 'is_weekend' για να πρέπει να την υπολογίσουμε εμείς αργότερα
    df = df.drop(columns=['is_weekend'])
    
    # 5. Αποθήκευση στο φάκελο data
    output_path = 'data/general_ledger_2023.csv'
    df.to_csv(output_path, index=False)
    print(f"✅ Δημιουργήθηκαν {num_records} εγγραφές με επιτυχία! Το αρχείο σώθηκε στο: {output_path}")

if __name__ == "__main__":
    generate_gl_data()