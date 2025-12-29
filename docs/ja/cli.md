# CLI リファレンス

## コマンド一覧

- `scan`: PDF を処理してノートを生成します
- `init`: 設定ファイルやテンプレート、DB を準備します
- `config`: 設定値を表示/初期化します
- `template`: ノートテンプレートを作成/切り替えます
- `doctor`: 設定や外部連携の状態を確認します

## scan

### 何をするコマンドか

PDF を処理してノートを生成します。

### 使い方

```bash
zotomatic scan [--once | --watch] [--force]
zotomatic scan --path <pdf...>
```

- `--once` / `--watch` は `pdf_dir` の設定が必要です。
- `--path` は `pdf_dir` の設定が不要です。

### モード (同時指定不可)

- `--once` (既定)
  - `pdf_dir` を一度スキャンして処理したら終了します。
  - 例: `zotomatic scan --once`
- `--watch`
  - 起動時に `pdf_dir` を一度スキャンし、以降は新規 PDF を監視して処理し続けます。
  - 終了は `Ctrl+C`。
  - 例: `zotomatic scan --watch`
- `--path <pdf...>`
  - 指定した PDF を順番に処理して終了します。
  - 例: `zotomatic scan --path ~/Downloads/a.pdf ~/Downloads/b.pdf`

### 追加オプション

- `--force`
  - 以前の処理でスキップされた PDF も対象にして走査します。
  - `--path` とは併用できません。
  - 例: `zotomatic scan --watch --force`

## init

### 何をするコマンドか

設定ファイルとテンプレートを初期化し、DB を用意します。2回目以降は既存の値を上書きせず、不足している設定やテンプレートだけを補完します。

### 使い方

```bash
zotomatic init --pdf-dir <path> [--note-dir <path>] [--template-path <path>]
```

### 何が作成されるか

- 設定ファイル:
  - macOS/Linux: `~/.zotomatic/config.toml`
  - Windows: `%LOCALAPPDATA%\\Zotomatic\\config.toml`
- テンプレート:
  - 既定: `~/Zotomatic/templates/note.md`
  - `--template-path` 指定時はそのパス
- SQLite DB:
  - macOS/Linux: `~/.zotomatic/db/zotomatic.db`
  - Windows: `%LOCALAPPDATA%\\Zotomatic\\db\\zotomatic.db`

### オプション

- `--pdf-dir` (必須)
  - 監視対象 PDF のルートディレクトリを指定します。
  - 例: `zotomatic init --pdf-dir ~/Zotero/storage`
- `--note-dir`
  - ノートの出力先を指定します (既定: `~/Zotomatic/notes`)。
  - 例: `zotomatic init --pdf-dir ~/Zotero/storage --note-dir ~/Documents/Obsidian/Zotomatic`
- `--template-path`
  - ノートテンプレートの保存先を指定します。
  - 例: `zotomatic init --pdf-dir ~/Zotero/storage --template-path ~/Zotomatic/templates/note.md`

既存設定がある場合は不足キーのみ追記され、テンプレートは未作成なら生成されます。

## config

### 何をするコマンドか

現在の設定値を表示したり、既定値に戻します。

### 使い方

```bash
zotomatic config
zotomatic config show
zotomatic config default
```

### サブコマンド

- `show`
  - マージ済みの有効設定値を表示します。
  - 例: `zotomatic config show`
- `default`
  - 設定を既定へ戻し、`config.toml.bak` を作成します。
  - 例: `zotomatic config default`

## template

### 何をするコマンドか

ノートテンプレートを作成または切り替えます。

### 使い方

```bash
zotomatic template create --path <path>
zotomatic template set --path <path>
```

### サブコマンド

- `create --path <path>`
  - 指定パスにテンプレートを新規作成し、`template_path` を更新します。
  - 例: `zotomatic template create --path ~/Zotomatic/templates/note.md`
- `set --path <path>`
  - 既存テンプレートを指定して `template_path` を更新します。
  - 例: `zotomatic template set --path ~/Zotomatic/templates/note.md`

## doctor

### 何をするコマンドか

設定ファイルやパス、外部連携の状態を確認します。

### 使い方

```bash
zotomatic doctor
```
