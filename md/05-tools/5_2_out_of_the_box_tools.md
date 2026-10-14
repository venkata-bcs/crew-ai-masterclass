# 5.2 Out-of-the-box Tools

[🏠 Home](../../README.md) · [⬅ 5.1 Types of Tools](5_1_types_of_tools.md) · [5.3 Third-party Tools ➡](5_3_third_party_tools.md)

> **Module 5 · Tools** · 💻 Code: [5_2_out_of_the_box_tools.py](../../code/05-tools/5_2_out_of_the_box_tools.py)

## In one sentence

The `crewai-tools` package gives you dozens of **ready-made tools**: create one, hand it to an agent, done.

## Popular built-in tools

| Category | Tools | What they do |
|---|---|---|
| **Files** | `DirectoryReadTool`, `FileReadTool`, `FileWriterTool` | List, read and write files |
| **Web** | `ScrapeWebsiteTool`, `WebsiteSearchTool` | Read or search a web page |
| **Search** | `SerperDevTool`, `BraveSearchTool` | Google-style web search (API key needed) |
| **Documents** | `PDFSearchTool`, `TXTSearchTool`, `CSVSearchTool` | Search inside documents (small RAG) |
| **Code** | `CodeInterpreterTool` | Run Python code |

Install once: `pip install crewai-tools`.

## The demo: a team secretary

The script creates 3 meeting-note files. The agent **finds** them, **reads** them, and **writes** a summary file, all with built-in tools:

```mermaid
flowchart LR
    D["📂 meeting_notes/<br/>monday · wednesday · friday"] -->|DirectoryReadTool| L["📋 list of files"]
    L -->|FileReadTool ×3| R["📄 note contents"]
    R --> A["🤖 Team Secretary"]
    A -->|FileWriterTool| S["📝 weekly_summary.md"]
```

```python
list_files = DirectoryReadTool(directory=str(notes_dir))   # locked to ONE folder
read_file  = FileReadTool()                                # reads any path the agent gives
write_file = FileWriterTool()                              # filename + content (+ directory)

secretary = Agent(role="Team Secretary", tools=[list_files, read_file, write_file], llm=llm, ...)
```

> **Configure tools when you create them.** `DirectoryReadTool(directory=...)` can only see that folder. Narrow tools are safer, especially tools that *write* things.

## Another example: the DataCamp walkthrough

A classic beginner pipeline from the [DataCamp CrewAI tutorial](https://www.datacamp.com/tutorial/crew-ai) chains web tools the same way:

```mermaid
flowchart LR
    W["🌐 Wikipedia page"] -->|ScrapeWebsiteTool| Txt["📄 raw text"]
    Txt -->|FileWriterTool| File["💾 ai.txt"]
    File -->|TXTSearchTool| Ctx["🔎 relevant passages"]
    Ctx --> Ag["🤖 Educator agent"] --> Ans["✅ Simple explanation"]
```

```python
text = ScrapeWebsiteTool(website_url="https://en.wikipedia.org/wiki/Artificial_intelligence").run()
FileWriterTool().run(filename="ai.txt", content=text, overwrite="True")
search = TXTSearchTool(txt="ai.txt")        # needs an embedder: see 7.2
educator = Agent(role="Educator", tools=[search], ...)
```

## Run it

```powershell
.venv\Scripts\python code\05-tools\5_2_out_of_the_box_tools.py
```

## What you'll see

```text
===== TOOL CALLS (in order) =====

  1. list_files_in_directory: {}
  2. read_a_files_content: {'file_path': '...\\meeting_notes\\monday.txt'}
  3. read_a_files_content: {'file_path': '...\\meeting_notes\\wednesday.txt'}
  4. read_a_files_content: {'file_path': '...\\meeting_notes\\friday.txt'}
  5. file_writer_tool: {'filename': 'weekly_summary.md', 'content': '# Weekly Summary\n\n## D...

===== weekly_summary.md =====

# Weekly Summary
## Decisions
- Launch the mobile app on 1 March (agreed Monday, reaffirmed Friday)
## Risks
- Launch at risk due to 3 login bugs identified Wednesday
- Risk mitigated: login bugs fixed by Friday
## Owners
- Ana: owns testing
- Raj: writes release notes
```

The agent planned the order itself: **list → read ×3 → write**. Notice it connected facts across files ("agreed Monday, reaffirmed Friday").

## Key takeaways

- `crewai-tools` covers the common jobs: files, web, search, documents, code.
- Configure tools when you create them, and keep write-tools narrow.
- Tool names in events/logs are tidied (`read_a_files_content`).

## Try it yourself

- Add a 4th note file (`thursday.txt`) with a new risk. Does it appear in the summary?

---

[🏠 Home](../../README.md) · [⬅ 5.1 Types of Tools](5_1_types_of_tools.md) · [5.3 Third-party Tools ➡](5_3_third_party_tools.md)
