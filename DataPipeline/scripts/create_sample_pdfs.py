#!/usr/bin/env python3
"""Generate realistic sample PDF documents for pipeline testing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def create_pdfs(output_dir: str = "./sample_data/samples") -> list[str]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch, cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        )
    except ImportError:
        print("reportlab not installed. Run: pip install reportlab")
        sys.exit(1)

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    created: list[str] = []

    created.append(_create_ml_paper(output_dir))
    created.append(_create_financial_report(output_dir))
    created.append(_create_technical_manual(output_dir))

    return created


def _create_ml_paper(output_dir: str) -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    path = str(Path(output_dir) / "machine_learning_fundamentals.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=18, spaceAfter=20)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14, spaceAfter=12)
    body = styles["BodyText"]
    body.spaceAfter = 10

    story.append(Paragraph("Machine Learning Fundamentals", title_style))
    story.append(Paragraph("Author: Dr. Jane Smith, PhD", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Abstract", h2))
    story.append(Paragraph(
        "Machine learning (ML) is a subset of artificial intelligence that enables systems to "
        "learn and improve from experience without being explicitly programmed. This paper provides "
        "a comprehensive overview of core ML concepts including supervised learning, unsupervised "
        "learning, reinforcement learning, and deep neural networks. We examine key algorithms, "
        "their mathematical foundations, and practical applications across various industries.",
        body
    ))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("1. Introduction", h2))
    story.append(Paragraph(
        "The field of machine learning has experienced exponential growth over the past decade, "
        "driven by advances in computational power, the availability of large datasets, and "
        "breakthroughs in algorithmic design. Today, ML powers recommendation systems at companies "
        "like Netflix and Amazon, enables autonomous vehicles at Tesla and Waymo, and underpins "
        "medical diagnostic tools that can detect cancer with superhuman accuracy.",
        body
    ))
    story.append(Paragraph(
        "Machine learning algorithms can be broadly categorized into three paradigms: supervised "
        "learning, unsupervised learning, and reinforcement learning. Each paradigm addresses "
        "different problem types and uses different training methodologies.",
        body
    ))

    story.append(Paragraph("2. Supervised Learning", h2))
    story.append(Paragraph(
        "Supervised learning involves training a model on labeled data, where each training "
        "example consists of an input-output pair. The goal is to learn a mapping function f(x) "
        "such that f(x) ≈ y for all training examples. Common supervised learning algorithms "
        "include Linear Regression, Logistic Regression, Decision Trees, Random Forests, "
        "Support Vector Machines (SVM), and Neural Networks.",
        body
    ))
    story.append(Paragraph(
        "Linear regression models the relationship between a dependent variable y and one or "
        "more independent variables X using the equation: y = β₀ + β₁x₁ + β₂x₂ + ... + βₙxₙ + ε, "
        "where β are coefficients and ε is the error term. The coefficients are estimated by "
        "minimizing the sum of squared residuals using the ordinary least squares (OLS) method.",
        body
    ))

    story.append(Paragraph("3. Neural Networks and Deep Learning", h2))
    story.append(Paragraph(
        "Artificial neural networks are computational models inspired by biological neural networks "
        "in the human brain. A neural network consists of layers of interconnected nodes (neurons). "
        "Deep learning refers to neural networks with many hidden layers, enabling the learning of "
        "complex hierarchical representations. Convolutional Neural Networks (CNNs) excel at image "
        "recognition tasks, while Recurrent Neural Networks (RNNs) and Transformers handle "
        "sequential data such as text and time series.",
        body
    ))

    story.append(Paragraph("4. Model Evaluation and Validation", h2))
    story.append(Paragraph(
        "Evaluating a machine learning model is critical to ensure it generalizes well to unseen "
        "data. Key evaluation metrics include: Accuracy (fraction of correct predictions), "
        "Precision (true positives / predicted positives), Recall (true positives / actual positives), "
        "F1-Score (harmonic mean of precision and recall), and AUC-ROC (area under the receiver "
        "operating characteristic curve). Cross-validation techniques such as k-fold cross-validation "
        "provide robust estimates of model performance.",
        body
    ))

    story.append(Paragraph("5. Conclusion", h2))
    story.append(Paragraph(
        "Machine learning represents one of the most transformative technologies of our era. "
        "From healthcare to finance, autonomous systems to natural language processing, ML "
        "continues to reshape industries and create new possibilities. As datasets grow larger "
        "and compute becomes cheaper, the potential for ML to solve increasingly complex real-world "
        "problems continues to expand. Future research directions include explainable AI, "
        "federated learning, and energy-efficient model architectures.",
        body
    ))

    doc.build(story)
    print(f"Created: {path}")
    return path


def _create_financial_report(output_dir: str) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    path = str(Path(output_dir) / "q4_financial_report_2024.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=18, spaceAfter=20)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14, spaceAfter=12)
    body = styles["BodyText"]
    body.spaceAfter = 10

    story.append(Paragraph("Q4 2024 Financial Report", h1))
    story.append(Paragraph("Acme Corporation Inc. | Fiscal Year 2024", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Executive Summary", h2))
    story.append(Paragraph(
        "Acme Corporation achieved record revenue of $4.2 billion in Q4 2024, representing "
        "a 23% year-over-year growth. Operating income increased to $890 million (21.2% margin), "
        "driven by strong performance in cloud services and international expansion. Free cash flow "
        "reached $1.1 billion, enabling significant investments in R&D and strategic acquisitions.",
        body
    ))

    story.append(Paragraph("Financial Highlights", h2))
    data = [
        ["Metric", "Q4 2024", "Q4 2023", "YoY Change"],
        ["Revenue", "$4.2B", "$3.4B", "+23.5%"],
        ["Gross Profit", "$2.1B", "$1.6B", "+31.3%"],
        ["Operating Income", "$890M", "$680M", "+30.9%"],
        ["Net Income", "$720M", "$540M", "+33.3%"],
        ["EPS (Diluted)", "$3.42", "$2.56", "+33.6%"],
        ["Free Cash Flow", "$1.1B", "$840M", "+31.0%"],
    ]
    t = Table(data, colWidths=[2.2 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.lightgrey, colors.white]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Revenue by Segment", h2))
    story.append(Paragraph(
        "Cloud Services revenue grew 45% to $2.1 billion, now representing 50% of total revenue. "
        "Enterprise Software revenue increased 18% to $1.3 billion. Consumer Products revenue "
        "declined 5% to $800 million due to increased competition in the smartphone market. "
        "International markets now account for 38% of total revenue, up from 30% in 2023.",
        body
    ))

    story.append(Paragraph("Outlook for 2025", h2))
    story.append(Paragraph(
        "Management provides the following guidance for fiscal year 2025: Total revenue is expected "
        "to be in the range of $17.5 to $18.2 billion, representing growth of 18-22%. Operating "
        "margin is expected to improve to 22-23%. Capital expenditures are projected at $1.8 billion, "
        "primarily for cloud infrastructure expansion and AI research facilities.",
        body
    ))

    doc.build(story)
    print(f"Created: {path}")
    return path


def _create_technical_manual(output_dir: str) -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    path = str(Path(output_dir) / "api_integration_guide.pdf")
    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=18, spaceAfter=20)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=14, spaceAfter=12)
    body = styles["BodyText"]
    body.spaceAfter = 10
    code = ParagraphStyle("Code", parent=styles["Code"], fontSize=9, backColor="#f5f5f5", leftIndent=20)

    story.append(Paragraph("REST API Integration Guide v2.0", h1))
    story.append(Paragraph("TechCorp Developer Documentation", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    story.append(Paragraph("Overview", h2))
    story.append(Paragraph(
        "The TechCorp REST API provides programmatic access to all platform features. The API "
        "follows RESTful principles and uses JSON for request and response bodies. Authentication "
        "uses OAuth 2.0 with Bearer tokens. The base URL for all API endpoints is "
        "https://api.techcorp.com/v2. Rate limits are enforced at 1000 requests per minute "
        "per API key.",
        body
    ))

    story.append(Paragraph("Authentication", h2))
    story.append(Paragraph(
        "To authenticate API requests, include an Authorization header with a Bearer token. "
        "Tokens are obtained via the OAuth 2.0 client credentials flow. Tokens expire after "
        "3600 seconds (1 hour) and must be refreshed using the refresh_token endpoint.",
        body
    ))
    story.append(Paragraph(
        "POST /oauth/token\nContent-Type: application/x-www-form-urlencoded\n"
        "grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_SECRET",
        code
    ))

    story.append(Paragraph("Core Endpoints", h2))
    story.append(Paragraph(
        "GET /documents — List all documents with pagination support (page, limit parameters). "
        "POST /documents — Upload a new document. Accepts multipart/form-data. "
        "GET /documents/{id} — Retrieve a specific document by ID. "
        "DELETE /documents/{id} — Delete a document. Returns 204 No Content on success. "
        "POST /documents/{id}/process — Trigger AI processing for a document.",
        body
    ))

    story.append(Paragraph("Error Handling", h2))
    story.append(Paragraph(
        "The API uses standard HTTP status codes: 200 OK (success), 201 Created (resource created), "
        "400 Bad Request (invalid parameters), 401 Unauthorized (missing or invalid auth token), "
        "403 Forbidden (insufficient permissions), 404 Not Found (resource does not exist), "
        "429 Too Many Requests (rate limit exceeded), 500 Internal Server Error (server-side error). "
        "All error responses include a JSON body with 'error' and 'message' fields.",
        body
    ))

    story.append(Paragraph("Webhooks", h2))
    story.append(Paragraph(
        "Webhooks allow your application to receive real-time notifications when events occur. "
        "Register a webhook endpoint via POST /webhooks with a URL and list of event types. "
        "Supported events include document.processed, document.failed, and batch.completed. "
        "Webhook payloads are signed using HMAC-SHA256. Verify the X-Signature header to ensure "
        "requests are authentic. Retry logic automatically resends failed webhook deliveries "
        "up to 5 times with exponential backoff.",
        body
    ))

    doc.build(story)
    print(f"Created: {path}")
    return path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create sample PDFs for pipeline testing")
    parser.add_argument("--output", default="./sample_data/samples", help="Output directory")
    args = parser.parse_args()

    files = create_pdfs(args.output)
    print(f"\n✓ Created {len(files)} sample PDFs in {args.output}")
