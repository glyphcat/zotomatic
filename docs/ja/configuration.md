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

## 設定キー一覧

| config キー | 環境変数キー | 区分 | 意味 |
| --- | --- | --- | --- |
| `note_dir` | `ZOTOMATIC_NOTE_DIR` | 任意 | 生成ノートの出力先ディレクトリ (未指定時は既定値)。 |
| `notes_encoding` | `ZOTOMATIC_NOTES_ENCODING` | 任意 | ノートの文字エンコーディング (既定: `utf-8`)。 |
| `pdf_dir` | `ZOTOMATIC_PDF_DIR` | 必須 | 監視対象となる PDF 格納ディレクトリ。 |
| `llm_output_language` | `ZOTOMATIC_LLM_OUTPUT_LANGUAGE` | 任意 | LLM 出力言語コード。指定できる言語コード: `en`, `ja`, `zh`, `ko`, `es`, `pt`, `fr`, `de`, `it`, `nl`, `sv`, `pl`, `tr`, `ru`。 |
| `llm_summary_mode` | `ZOTOMATIC_LLM_SUMMARY_MODE` | 任意 | 要約モード: `quick`, `standard`, `deep`。 |
| `tag_generation_limit` | `ZOTOMATIC_TAG_GENERATION_LIMIT` | 任意 | タグ生成の最大数。 |
| `llm_tag_enabled` | `ZOTOMATIC_LLM_TAG_ENABLED` | 任意 | LLM によるタグ生成を有効化。 |
| `llm_summary_enabled` | `ZOTOMATIC_LLM_SUMMARY_ENABLED` | 任意 | LLM による要約生成を有効化。 |
| `llm_openai_api_key` | `ZOTOMATIC_LLM_OPENAI_API_KEY` | 条件付き必須 | OpenAI を使う場合に必要。 |
| `llm_timeout` | `ZOTOMATIC_LLM_TIMEOUT` | 任意 | LLM API リクエストのタイムアウト秒数 (既定: `30.0`、TOML の float で指定)。 |
| `llm_daily_limit` | `ZOTOMATIC_LLM_DAILY_LIMIT` | 任意 | LLM 実行回数の 1 日あたり上限。 |
| `zotero_api_key` | `ZOTOMATIC_ZOTERO_API_KEY` | 条件付き必須 | Zotero 解決を使う場合に必要。 |
| `zotero_library_id` | `ZOTOMATIC_ZOTERO_LIBRARY_ID` | 任意 | Zotero ライブラリ ID (空ならユーザー)。 |
| `zotero_library_scope` | `ZOTOMATIC_ZOTERO_LIBRARY_SCOPE` | 任意 | Zotero のスコープ: `user` / `group`。 |
| `note_title_pattern` | `ZOTOMATIC_NOTE_TITLE_PATTERN` | 任意 | ノートのファイル名テンプレート (未指定時は既定値)。 |
| `template_path` | `ZOTOMATIC_TEMPLATE_PATH` | 任意 | ノートテンプレートのパス (未指定時は既定値)。 |

区分の意味:

- 必須: 機能の利用に必要 (未設定だとエラー/無効)
- 条件付き必須: 特定機能を使う場合のみ必要
- 任意: 上書きしない限りデフォルトで動作

## 文字エンコーディングについて

`notes_encoding` は指定可能ですが上級者向けです。基本は `utf-8` を推奨します。

## LLM 出力言語について

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

## 環境変数

上記の環境変数キーのみを受け付けます。接頭辞を除去して小文字化したものが設定キーになります。

例:

```bash
export ZOTOMATIC_LLM_OPENAI_API_KEY=...
```

注意: `notes_encoding` / `llm_timeout` は `config.toml` での指定を推奨します。

## 例

```toml
llm_openai_api_key = "sk-..."
pdf_dir = "~/Zotero/storage"
note_dir = "~/Documents/Obsidian/Zotomatic"
note_title_pattern = "{{ year }}-{{ slug80 }}-{{ citekey }}"
template_path = "~/Zotomatic/templates/note.md"
```
