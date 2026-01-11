# 設定リファレンス

このドキュメントは、ユーザーが設定ファイルまたは環境変数で指定できる設定値をまとめたものです。

## 設定ファイルの場所

- macOS/Linux: `~/.zotomatic/config.toml`
- Windows: `%LOCALAPPDATA%\\Zotomatic\\config.toml`

## 読み込み優先順位

1. CLI から渡されたオプション
2. 環境変数 (`ZOTOMATIC_` で始まるもの)
3. 設定ファイル
4. パッケージ既定値

## バージョン確認

インストール済みバージョンは `zotomatic --version` で確認できます。

## 設定キー一覧

### 基本設定

| config キー | 環境変数キー | 区分 | 意味 |
| --- | --- | --- | --- |
| `note_dir` | `ZOTOMATIC_NOTE_DIR` | 任意 | 生成ノートの出力先ディレクトリ。 |
| `notes_encoding` | `ZOTOMATIC_NOTES_ENCODING` | 任意 | ノートの文字エンコーディング。 |
| `pdf_dir` | `ZOTOMATIC_PDF_DIR` | 必須 | 監視対象となる PDF 格納ディレクトリ。 |
| `llm_output_language` | `ZOTOMATIC_LLM_OUTPUT_LANGUAGE` | 任意 | LLM 出力言語コード。指定できる言語コード: `en`, `ja`, `zh`, `ko`, `es`, `pt`, `fr`, `de`, `it`, `nl`, `sv`, `pl`, `tr`, `ru`。 |
| `llm_summary_mode` | `ZOTOMATIC_LLM_SUMMARY_MODE` | 任意 | 要約モード: `quick`, `standard`, `deep`。 |
| `llm_tag_limit` | `ZOTOMATIC_LLM_TAG_LIMIT` | 任意 | タグ生成の最大数。 |
| `llm_tag_enabled` | `ZOTOMATIC_LLM_TAG_ENABLED` | 任意 | LLM によるタグ生成を有効化。 |
| `llm_summary_enabled` | `ZOTOMATIC_LLM_SUMMARY_ENABLED` | 任意 | LLM による要約生成を有効化。 |
| `llm_timeout` | `ZOTOMATIC_LLM_TIMEOUT` | 任意 | LLM API リクエストのタイムアウト秒数 (TOML の float で指定)。 |
| `llm_daily_limit` | `ZOTOMATIC_LLM_DAILY_LIMIT` | 任意 | LLM 実行回数の 1 日あたり上限。 |
| `zotero_api_key` | `ZOTOMATIC_ZOTERO_API_KEY` | 条件付き必須 | Zotero 解決を使う場合に必要。 |
| `zotero_library_id` | `ZOTOMATIC_ZOTERO_LIBRARY_ID` | 任意 | Zotero ライブラリ ID (空ならユーザー)。 |
| `zotero_library_scope` | `ZOTOMATIC_ZOTERO_LIBRARY_SCOPE` | 任意 | Zotero のスコープ: `user` / `group`。 |
| `note_title_pattern` | `ZOTOMATIC_NOTE_TITLE_PATTERN` | 任意 | ノートのファイル名テンプレート。 |
| `template_path` | `ZOTOMATIC_TEMPLATE_PATH` | 任意 | ノートテンプレートのパス。 |

### LLM 設定

LLM は `[llm]` と `[llm.providers.<provider>]` で設定します。`llm.provider` は必須です。
ドキュメント上は ChatGPT と表記していますが、設定値は `openai` を使用します。

| config キー | 環境変数キー | 区分 | 意味 |
| --- | --- | --- | --- |
| `llm.provider` | `ZOTOMATIC_LLM_PROVIDER` | 条件付き必須 | LLM プロバイダ (`openai` / `gemini`)。 |
| `llm.providers.openai.api_key` | `ZOTOMATIC_LLM_OPENAI_API_KEY` | 条件付き必須 | ChatGPT(OpenAI) を使う場合に必要。 |
| `llm.providers.openai.model` | `ZOTOMATIC_LLM_OPENAI_MODEL` | 任意 | ChatGPT のモデル名。 |
| `llm.providers.openai.base_url` | `ZOTOMATIC_LLM_OPENAI_BASE_URL` | 任意 | ChatGPT のベース URL。 |
| `llm.providers.gemini.api_key` | `ZOTOMATIC_LLM_GEMINI_API_KEY` | 条件付き必須 | Gemini を使う場合に必要。 |
| `llm.providers.gemini.model` | `ZOTOMATIC_LLM_GEMINI_MODEL` | 任意 | Gemini のモデル名。 |
| `llm.providers.gemini.base_url` | `ZOTOMATIC_LLM_GEMINI_BASE_URL` | 任意 | Gemini のベース URL。 |

区分の意味:

- 必須: 機能の利用に必要 (未設定だとエラー/無効)
- 条件付き必須: 特定機能を使う場合のみ必要
- 任意: 上書きしない限りデフォルトで動作

### デフォルト値一覧

| キー | デフォルト値 |
| --- | --- |
| `note_dir` | `~/Zotomatic/notes` |
| `notes_encoding` | `utf-8` |
| `llm_output_language` | `ja` |
| `llm_summary_mode` | `quick` |
| `llm_tag_limit` | `8` |
| `llm_tag_enabled` | `true` |
| `llm_summary_enabled` | `true` |
| `llm_timeout` | `30.0` |
| `llm_daily_limit` | `50` |
| `zotero_api_key` | `(空)` |
| `zotero_library_id` | `(空)` |
| `zotero_library_scope` | `user` |
| `note_title_pattern` | `{{ year }}-{{ slug80 }}-{{ citekey }}` |
| `template_path` | `~/Zotomatic/templates/note.md` |
| `llm.provider` | `(空)` |
| `llm.providers.openai.model` | `gpt-4o-mini` |
| `llm.providers.openai.base_url` | `https://api.openai.com/v1` |
| `llm.providers.gemini.model` | `gemini-2.0-flash` |
| `llm.providers.gemini.base_url` | `https://generativelanguage.googleapis.com/v1beta` |

### 設定ファイル　（config.toml）

```toml
pdf_dir = "~/Zotero/storage"
note_dir = "~/Documents/Obsidian/Zotomatic"
note_title_pattern = "{{ year }}-{{ slug80 }}-{{ citekey }}"
template_path = "~/Zotomatic/templates/note.md"

[llm]
provider = "openai"

[llm.providers.openai]
api_key = "sk-..."
```

### 環境変数

一覧の環境変数キーのみが有効です。接頭辞を除去して小文字化したものが設定キーになります。
LLM は `ZOTOMATIC_LLM_PROVIDER` と各プロバイダのキー (`ZOTOMATIC_LLM_OPENAI_API_KEY` など) を組み合わせて指定します。

例:

```bash
export ZOTOMATIC_LLM_PROVIDER=openai
export ZOTOMATIC_LLM_OPENAI_API_KEY=...
```

注意: `notes_encoding` / `llm_timeout` は `config.toml` での指定を推奨します。

## `notes_encoding` (出力文字エンコーディング) について

`notes_encoding` は指定可能ですが上級者向けです。基本は `utf-8` を推奨します。

## `llm_output_language` (LLM 出力言語) について

`llm_output_language` はプロンプトに指定言語を埋め込むだけの設定です。各言語の出力品質や正確性を保証するものではありません。

### 言語コード対応表

| 言語コード | 言語 |
| --- | --- |
| `de` | Deutsch |
| `en` | English |
| `es` | Español |
| `fr` | Français |
| `it` | Italiano |
| `ja` | 日本語 |
| `ko` | 한국어 |
| `nl` | Nederlands |
| `pl` | Polski |
| `pt` | Português |
| `ru` | Русский |
| `sv` | Svenska |
| `tr` | Türkçe |
| `zh` | 中文 |

## `llm_summary_mode` (要約モード) について

`llm_summary_mode` は要約の詳細度を切り替えます。

- `quick`: アブストラクト中心の短い要約。
- `standard`: アブストラクトと各セクションの抜粋を使った要約。
- `deep`: 本文を分割して要約し、最後に統合する詳細要約。

実行ごとに一時上書きする場合は `zotomatic scan --summary-mode <mode>` を使います（設定ファイルは変更されません）。

## `note_title_pattern` (ノート名テンプレート) について

`note_title_pattern` は `{{ key }}` 形式のプレースホルダーを使ってファイル名を組み立てます。値が空の場合は空文字になります。拡張子が指定されていない場合は `.md` が付与され、ファイル名は安全な文字に置き換えられます。

### 使用できるプレースホルダー

| プレースホルダー | 説明 |
| --- | --- |
| `title` | 論文タイトル。Zotero 由来のタイトル、または PDF 名から補完された値。 |
| `citekey` | Zotero の citekey。無い場合は空。 |
| `year` | 年。 |
| `authors` | 著者文字列。 |
| `venue` | 出版元 (ジャーナル/会議名)。 |
| `doi` | DOI。 |
| `url` | URL。 |
| `source_url` | Zotero 由来の派生 URL。 |
| `zotero_select_uri` | Zotero の選択 URI。 |
| `pdf_path` | PDF のパス。 |
| `tags` | タグ文字列 (カンマ区切り)。 |
| `tags_list` | タグのリストを文字列化した値。 |
| `abstract` | アブストラクト。 |
| `zotero_abstract` | Zotero 由来のアブストラクト (実質 `abstract` と同等)。 |
| `generated_summary` | LLM 要約 (有効時のみ)。 |
| `highlights` | ハイライト。 |
| `zotero_highlights` | Zotero 注釈由来のハイライト。 |
| `zotomatic_summary_status` | 要約ステータス (`pending` など)。 |
| `zotomatic_summary_mode` | 要約モード (`quick` / `standard` / `deep`)。 |
| `zotomatic_tag_status` | タグステータス (`pending` など)。 |
| `zotomatic_last_updated` | 最終更新日時 (ISO 8601)。 |
| `slug80` | `title` / `citekey` / `year` から生成する 80 文字のスラッグ。 |
| `slug40` | `title` / `citekey` / `year` から生成する 40 文字のスラッグ。 |
