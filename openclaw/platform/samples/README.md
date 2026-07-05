# Sample Workflows

Ready-to-load workflow definitions that demonstrate ClawFlow's capabilities using
**real discovered tools** from the agents-tools-library. Every file is a valid DAG
and references only tool ids that exist in the registry.

Load them all into the platform:

```powershell
cd platform/backend
python -m scripts.seed_samples
```

…or import an individual file via the API / the **AI Builder** dialog.

| File | Demonstrates | Tools / nodes used |
|------|--------------|--------------------|
| [`email_attachment_archiver.json`](./email_attachment_archiver.json) | The spec's canonical example — read invoice emails, save attachments, archive, flag. | `outlook.read_outlook_mails`, `outlook.save_email_attachment`, `outlook.flag_email`, `action.file_write` |
| [`ach_exception_monitor.json`](./ach_exception_monitor.json) | Cron trigger → agent classification → **if/else branch** → **human approval** (approved/rejected) → notify. | `outlook.search_outlook_email`, `excel_tools.excel_write`, `agent.executor`, `logic.approval`, `action.send_email` |
| [`pdf_invoice_to_db.json`](./pdf_invoice_to_db.json) | File-upload trigger → **parallel** PDF extracts → **merge** → reviewer agent → SQL insert. | `pdf_tools.pdf_extract_tables`, `pdf_tools.pdf_extract_text`, `data_storage_tools.connect`, `data_storage_tools.insert_rows`, `agent.reviewer` |
| [`web_scrape_to_excel.json`](./web_scrape_to_excel.json) | Full Selenium browser-automation chain → Excel → email. | `web_tools.launch_browser`, `navigate_to_url`, `wait_for_element`, `extract_table`, `close_browser`, `excel_tools.excel_write` |
| [`multi_agent_research.json`](./multi_agent_research.json) | **Multi-agent collaboration**: planner → 2× research (parallel) → merge → reviewer → report → WhatsApp. | `agent.planner`, `agent.research`, `agent.reviewer`, `logic.parallel`, `logic.merge`, `action.send_whatsapp` |
| [`invoice_intake.json`](./invoice_intake.json) | Email trigger, executor agent, value-threshold approval, conditional recording. | `pdf_tools.pdf_extract_text`, `excel_tools.excel_write`, `logic.if_else`, `logic.approval` |
| [`daily_report.json`](./daily_report.json) | Scheduled research agent → report → email. | `agent.research`, `action.generate_report`, `action.send_email` |

> Notes
> - Agent and action nodes that call an LLM need a provider key (e.g. `ANTHROPIC_API_KEY`
>   or `GROQ_API_KEY`); without one they return a structured error and the rest of the
>   run continues.
> - Tool nodes that touch external systems (Outlook, a browser, a database) require
>   those to be available on the host — they're real integrations, not mocks.
> - `{{ ... }}` templates wire data between nodes, e.g. `{{ trigger.payload.file_path }}`
>   or `{{ nodes.review.output.output }}`.
