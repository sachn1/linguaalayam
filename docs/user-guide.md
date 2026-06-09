# User Guide

LinguAalayam is a Malayalam dictionary search engine. Search by word, by approximate spelling, or by meaning — in English or Malayalam.

**Live at [linguaalayam.org](https://linguaalayam.org)**

---

## Search modes

### Quick (default)
Finds words with similar spelling using trigram similarity. Good for:
- Approximate matches: *runing* → *running*
- Partial words: *ephem* → *ephemeral*
- When you're unsure of spelling

### Exact
Case-insensitive exact headword match. Returns every dictionary entry whose headword matches precisely.
Use when you know the exact spelling: *run*, *ഓടുക*, *ephemeral*.

### Smart
Searches by **meaning** using multilingual sentence embeddings. No API key required — this runs on our server.

Type a description, phrase, or concept:
- *"complete absence of sound"* → finds *silence*, *quiet*, *ശബ്ദമില്ലാത്ത*
- *"feeling of nostalgia"* → finds *longing*, *wistfulness*
- *"to move quickly on foot"* → finds *run*, *sprint*, *ഓടുക*
- *"what does ephemeral mean"* → finds *ephemeral* and related words

Smart mode works regardless of whether you have an API key. The LLM key only changes **how the results are presented** — without a key you get the raw entries; with a key you get a prose explanation.

---

## Corpora (source filter)

LinguAalayam searches three open corpora from [olam.in/p/open](https://olam.in/p/open). Leave the filter on **All corpora** to search all three at once.

| Corpus | Direction | Best for |
|---|---|---|
| **Olam** | English → Malayalam | Translating an English word to Malayalam |
| **Datuk** | Malayalam → Malayalam | Understanding a Malayalam word in depth |
| **Ekkurup** | English thesaurus | Finding synonyms and Malayalam equivalents for an English concept |

---

## AI synthesis (optional)

By default, results are raw dictionary entries. Add an API key in [Settings](/settings) to enable AI synthesis — the app reads the top results and writes a plain-English explanation.

**This is optional.** Smart search, Quick, and Exact modes all work without any key.

### How to get a key

| Provider | Where to get a key | Key format |
|---|---|---|
| Anthropic (Claude) | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) | `sk-ant-…` |
| OpenAI (GPT) | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | `sk-…` |

Both providers offer free-tier or pay-as-you-go access. For casual dictionary use, costs are negligible (fractions of a cent per query).

**Privacy:** your key is stored only in your browser's `localStorage`. It is sent directly to the AI provider with each request and is never stored on LinguAalayam's servers.

---

## Tips

- **Mixed-language search:** you can type in English or Malayalam in any mode.
- **Natural language in Smart mode:** phrasing like *"what does ephemeral mean"* or *"translate water to Malayalam"* works — the app extracts the word automatically.
- **No results?** Try switching from Exact to Quick or Smart. Also try removing the corpus filter.
- **MCP for AI assistants:** LinguAalayam is available as an MCP server at `https://linguaalayam.org/mcp`. See the [MCP setup guide](../linguaalayam/mcp/README.md) to connect Claude, Cursor, Windsurf, or Cline.

---

## Data sources

All corpora are from the [Olam open-data initiative](https://olam.in/p/open), a free Malayalam dictionary project. Dataset citations and licence information are available on that page.

---

## Feedback and issues

Something not working? A word missing? [Open an issue on GitHub](https://github.com/sachn1/linguaalayam/issues/new).
