import fitz  # PyMuPDF

def merge_pdfs(pdf_list, output_pdf):
    merged_pdf = fitz.open()
    
    for pdf in pdf_list:
        with fitz.open(pdf) as doc:
            merged_pdf.insert_pdf(doc)
    
    merged_pdf.save(output_pdf)
    merged_pdf.close()

# Example usage
pdf_files = ["file1.pdf", "file2.pdf", "file3.pdf","file4.pdf","file5.pdf","file6.pdf"]
merge_pdfs(pdf_files, "merged_output1.pdf")

print("PDFs merged successfully!")
