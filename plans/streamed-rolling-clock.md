# 固定比率ポートフォリオのリスク・リターン図示

## Context
最適化結果（最大シャープ・最小分散・目標リターン）に加えて、ユーザーが決めた固定比率（例：均等配分、60/40）が効率的フロンティア上のどこにあるかを見たい。
決定事項：**分析後に結果画面で比率を入力**して即時に反映する。**固定比率ポートフォリオは1つ**。
データの再取得やシミュレーションの再実行はしない。分析結果に含まれる年率の期待リターンと共分散行列から、サーバー側で指標を計算する。

## 方針
年率の期待リターン（`asset_statistics[*].expected_return`）と共分散行列が分かれば、`calculate_portfolio_metrics()` だけでリスク・リターン・シャープレシオ・VaRが出る。
そこで、analyze のレスポンスに共分散行列と無リスク金利を追加し、それを使って比率を評価する軽量のAPIを1本追加する。
図への反映は、結果に `custom_portfolio` を足して既存の `/api/visualize` で再描画する。

## 変更内容

### 1. `src/app/utils/calculator.py`
- `load_statistics(mean_returns: pd.Series, cov_matrix: pd.DataFrame, risk_free_rate: float)` を追加する。
  - `mean_returns` / `cov_matrix` / `risk_free_rate` だけを設定する（`returns` は None のまま）。
  - これにより既存の `calculate_portfolio_metrics()`（[calculator.py:105](src/app/utils/calculator.py#L105)）をそのまま使える。
- リスク寄与（`risk_decomposition`）は `self.returns` が必要で、今回の範囲外のため対象外とする。

### 2. `src/app/api/portfolio.py`
- `/api/analyze` の結果に以下を追加する：
  - `results['covariance_matrix'] = calculator.cov_matrix.to_dict()`
  - `results['risk_free_rate'] = risk_free_rate`
  - フォームの値は分析後に変更されている可能性があるため、分析時の値を返す。
- 新しいエンドポイント `POST /api/evaluate-portfolio` を追加する。
  - リクエスト：`{weights: {T: w}, expected_returns: {T: r}, covariance_matrix: {T: {T: c}}, risk_free_rate}`
  - 検証項目（違反時は 400）：
    - 3つのキー集合が一致すること。資産数は 2〜`MAX_ASSETS`。
    - 値がすべて有限の数値であること。
    - 各比率が 0〜1（既存の最適化と同じロングオンリー）。
    - 比率の合計が 1 ± 0.001。
  - レスポンス：`{success, custom_portfolio: {weights, metrics}}`
    - `metrics` は `calculate_portfolio_metrics()` の戻り値で、最適ポートフォリオと同じ形。

### 3. `src/app/utils/visualizer.py`
- ヘルパー `_add_custom_portfolio_trace(fig, custom_portfolio)` を追加する。
  - マーカーは既存と区別する（例：`symbol='x'`、黒系、size 14）。凡例名は `_('Fixed Weights')`。
  - ホバーには、リスク・リターン・シャープレシオと配分比率を出す（既存のホバー文字列作成と同じ書き方）。
- 呼び出し元：
  - `create_efficient_frontier_plot()` と `create_working_efficient_frontier_plot()` に引数 `custom_portfolio: Optional[Dict] = None` を追加し、末尾でヘルパーを呼ぶ。
  - `create_summary_dashboard()`（[visualizer.py:368](src/app/utils/visualizer.py#L368)〜）と `/api/visualize` の個別分岐では、`analysis_results.get('custom_portfolio')` を渡す。

### 4. フロントエンド
- `src/app/templates/index.html`：効率的フロンティアのタブで、`#frontierChart` の下に「固定比率」カードを置く。
  - 各銘柄の % 入力欄（JSで生成）、合計の表示、「プロット」「クリア」ボタン、結果の指標表示欄を置く。
  - 文言は `{{ _('...') }}` で書く。
- `src/app/static/js/portfolio.js`：
  - `setupFixedWeightsForm(results)`
    - 分析が終わるたびに呼ぶ（`main.js` の `currentResults = result` の後）。
    - `asset_statistics` の銘柄順で入力欄を作り、初期値は均等配分にする。
    - 入力が変わるたびに合計 % を表示し、100% でなければ「プロット」を無効にする。
  - `plotFixedWeights()`
    - % を小数にして `/api/evaluate-portfolio` に POST する。
    - `currentResults.custom_portfolio` に結果を入れ、`generateCharts(currentResults)` で再描画し、指標を表示する。
  - クリアの処理：`delete currentResults.custom_portfolio` してから再描画する。
- 新しく分析すると `currentResults` が置き換わるため、固定比率は自然にリセットされる。

### 5. 翻訳
- `pybabel extract / update / compile` を実行し、`ja/LC_MESSAGES/messages.po` に訳を追加する。
  - 対象の文言：「固定比率」「プロット」「クリア」「合計」など。

## テスト
- `tests/test_calculator.py`：`load_statistics()` 経由の `calculate_portfolio_metrics()` が、`load_data()` 経由の結果と一致すること。
- `tests/test_api_portfolio.py`：
  - `/api/evaluate-portfolio` の正常系。
  - 異常系：合計≠1、負の比率、銘柄の不一致、非数値、空のボディ。
  - `/api/analyze` のレスポンスに `covariance_matrix` と `risk_free_rate` が含まれること。
- `tests/test_visualizer.py`：`custom_portfolio` を渡すと、両方のフロンティア図に `Fixed Weights` のトレースが追加されること。渡さなければ追加されないこと。
- `tests/test_frontend_e2e.py`（既存の fake fetcher を利用）：分析 → 比率を入力 → プロットで、マーカーが図に出て指標が表示されること。

## 確認手順
1. `pytest tests/`
2. `python src/run.py` で SPY / ACWI / AGG を分析する。
3. 均等配分でプロットし、マーカーがフロンティアの内側（右下側）に出ることを確認する。
4. 最大シャープの配分を入力すると、★と同じ位置に重なることを確認する。
