import pdfplumber
import csv

def process_pdf_old(input, output, password, debugLog=False):
    pdf = pdfplumber.open(input, password=password)
    pages = pdf.pages

    total_amount=0.0
    
    indian = []
    foreign = []
    
    for page in pages:
        if page.extract_text().find("Domestic Transactions") > 0:
            print("Domestic") if debugLog else 0
            
            for (index, row) in enumerate(page.extract_table()):  # ty:ignore[invalid-argument-type]
                if index == 0 or row[0] == "" or row[0] == None:
                    continue

                amount_index = len(row) - 2
                
                print(row) if debugLog else 0

                indian.append({
                    "date": row[0].replace("null",""),
                    "description": row[1],
                    "currency": "INR",
                    "forex_amount": "",
                    "forex_rate": "",
                    "amount": row[amount_index].replace("Cr",""),
                    "type": "Cr" if "Cr" in row[amount_index] else "Dr"
                })
        
                total_amount += sum(float(item["amount"].replace(",","")) * (0 if item["type"] == "Cr" else 1) for item in indian)

        elif page.extract_text().find("International Transactions") > 0:
            print("Foreign") if debugLog else 0

            # Foreign transactions
            table_settings={
                "explicit_vertical_lines": [380] # Split the currency
            }
            
            for (index, row) in enumerate(page.extract_table(table_settings=table_settings)):  # ty:ignore[invalid-argument-type]

                if index == 0 or row[0] == "" or row[0] == None:
                    continue
                
                amount_index = len(row) - 2
                
                print(row) if debugLog else 0

                foreign.append({
                    "date": row[0].replace("null",""),
                    "description": row[1],
                    "currency": row[2][0:3],
                    "forex_amount": row[2][4:],
                    "forex_rate": '%.2f' % (float(row[amount_index].replace("Cr", "").replace(" ", "").replace(",",""))/float(row[2][4:].replace(",",""))),
                    "amount": row[amount_index].replace("Cr","").replace(" ", "").replace(",",""),
                    "type": "Cr" if "Cr" in row[amount_index] else "Dr"
                })

            # Credits in foreign statements are marked as deduction
            total_amount += sum(float(item["amount"].replace(",","")) * (-1 if item["type"] == "Cr" else 1) for item in foreign)

    print("Processed " + input + ". Total due should be " + str(total_amount)) if debugLog else 0

    # Output to CSV
    combined = []
    combined.extend(indian)
    combined.extend(foreign)

    cols = ["Date","Withdrawals","Deposits","Payee","Description","Reference Number"]
    with open(output, 'w') as file:
        writer = csv.DictWriter(file, delimiter=',', lineterminator='\n', quoting=csv.QUOTE_ALL, fieldnames=cols)
        writer.writeheader()

        for row in combined:

            formatted = {
                "Date": row.get("date", "").strip(),
                "Withdrawals": row["amount"] if row["type"] == "Dr" else "",
                "Deposits": row["amount"] if row["type"] == "Cr" else "",
                "Payee": "",
                "Description": row.get('description', ''),
                "Reference Number": f"Forex: {row['forex_amount']} {row['currency']} @ {row['forex_rate']}" if row.get('forex_amount') else ""
            }
            writer.writerow(formatted)