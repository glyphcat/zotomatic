# 使い始める

## 1. インストール

```bash
pip install zotomatic
```

## 2. 初期化 (初回のみ)

最初に設定ファイルとテンプレートを用意します。

```bash
zotomatic init --pdf-dir "~/Zotero/storage"
```

`--pdf-dir` は必須です。2回目以降の実行では既存の値を上書きせず、不足している設定やテンプレートだけを補完します。

設定ファイルの既定パス:

- macOS/Linux: `~/.zotomatic/config.toml`
- Windows: `%LOCALAPPDATA%\\Zotomatic\\config.toml`

## 3. 設定ファイルを確認・編集

最低限 `pdf_dir` を設定してください。その他の設定は必要に応じて調整します。

- `pdf_dir`: 監視対象 PDF のルート (必須)
- `note_dir`: ノートの出力先 (未指定なら既定値)
- `note_title_pattern` / `template_path`: ノート名・テンプレート (未指定なら既定値)
- `zotero_api_key` / `zotero_library_id`: Zotero 連携を使う場合に必要
- `llm_openai_api_key`: LLM による要約/タグ生成を使う場合に必要

Zotero 連携でリッチなメタデータを使う場合は、Zotero デスクトップアプリを起動しておくのが基本です。起動していない場合や Zotero 管理外の PDF でも、最小限のノートは生成できます。

設定例:

```toml
pdf_dir = "~/Zotero/storage"
note_dir = "~/Documents/Notes/Zotomatic"
note_title_pattern = "{{ year }}-{{ slug80 }}-{{ citekey }}"
template_path = "~/Zotomatic/templates/note.md"
```

設定値の変更は `config.toml` または環境変数で行います。環境変数の一覧は `configuration.md` を参照してください。

## 4. 事前チェック (推奨)

```bash
zotomatic doctor
```

標準的な運用 (pdf_dir を使った scan) が動くかを確認できます。`scan --path` だけを使う場合は、pdf_dir が未設定でも構いません。

## 5. ノート生成 (scan)

`scan` は 3 つのモードがあります。モードは同時指定できません。

### `--once` (既定)

`pdf_dir` を一度だけ走査して終了します。

```bash
zotomatic scan --once
```

### `--watch`

起動時に一度走査し、その後は新規 PDF を監視して処理します。終了は `Ctrl+C` です。

```bash
zotomatic scan --watch
```

### `--path <pdf...>`

指定した PDF を順番に処理して終了します。`pdf_dir` の設定は不要です。

```bash
zotomatic scan --path ~/Downloads/a.pdf ~/Downloads/b.pdf
```

### `--force` (再走査)

`--once` / `--watch` で、過去の走査結果によりスキップされた PDF も対象にします。既存ノートがある場合は更新・スキップの判定はそのまま行われます。

```bash
zotomatic scan --once --force
```

## 6. LLM 要約/タグ生成 (任意)

`llm_openai_api_key` を設定すると、要約やタグを自動でノートに挿入できます。未設定の場合はノート生成のみ行われ、要約/タグは無効になります。
