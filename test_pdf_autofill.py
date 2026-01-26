"""
Quick test for PDF auto-fill functionality
"""

from services.pdf_parser import PDFClaimParser
from pathlib import Path

# Test with sample PDF
pdf_path = Path("sample+claim_form.pdf")

if pdf_path.exists():
    print(f"✅ Found sample PDF: {pdf_path}")
    
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    print(f"📄 PDF size: {len(pdf_bytes)} bytes")
    
    # Test extraction
    print("\n🔄 Testing PDF extraction...")
    parsed = PDFClaimParser.parse_from_pdf_bytes(pdf_bytes)
    
    if parsed:
        print("\n✅ PDF parsed successfully!")
        print("\nExtracted fields:")
        for key, value in parsed.items():
            if value:
                print(f"  {key}: {value}")
    else:
        print("\n⚠️ Could not extract data from PDF")
        print("This is normal if PDF contains only images or encrypted content")
        print("Users can still fill form manually")
else:
    print(f"⚠️ Sample PDF not found: {pdf_path}")
    print("Creating a test with sample text instead...")
    
    # Test with text content
    sample_text = """
    PATIENT NAME: John Doe
    DATE OF BIRTH: 01/15/1980
    MEMBER ID: MEM123456789
    
    PROVIDER: Jane Smith, MD
    NPI: 1234567890
    
    SERVICE DATE: 12/15/2024
    CPT CODE: 99213
    DIAGNOSIS: J45.901
    CHARGES: $150.00
    """
    
    parsed = PDFClaimParser.parse_claim_data(sample_text)
    
    print("\n✅ Parsed sample text:")
    for key, value in parsed.items():
        if value:
            print(f"  {key}: {value}")
