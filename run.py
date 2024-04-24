
import argparse
import os
from plumber import process_pdf

def main(args):
    for file_name in os.listdir(args.in_dir):
        root, ext = os.path.splitext(file_name)
        if ext.lower() != '.pdf':
            continue

        pdf_path = os.path.join(args.in_dir, file_name)

        out_name = root + '.csv'
        out_path = os.path.join(args.out_dir, out_name)

        print(f'Processing: {pdf_path}')
        process_pdf(pdf_path, out_path, args.password, True)
        print(f'Output file: {out_path}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--in-dir', type=str, required=True, help='directory to read statement PDFs from.')
    parser.add_argument('--out-dir', type=str, required=True, help='directory to store statement CSV to.')
    parser.add_argument('--password', type=str, default=None, help='password for the statement PDF.')
    args = parser.parse_args()

    main(args)