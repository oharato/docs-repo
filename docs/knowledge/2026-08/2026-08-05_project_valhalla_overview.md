# OpenJDK Project Valhalla の概要と詳細解説

**調査日時**: 2026-08-05  
**概要**: OpenJDKにおける次世代Javaメモリモデル・型システム改革プロジェクト「Project Valhalla」の背景、目的、主要概念、および最新動向についてのまとめ。

---

## 1. Project Valhalla とは？ (要約)

**Project Valhalla** は、OpenJDK（Javaの開発コミュニティ）が進めている大規模なプロジェクトで、**Javaの型システムとメモリレイアウトを刷新し、高速化と効率化を図る取り組み**です。

キャッチフレーズは：  
> **"Codes like a class, works like a primitive"**  
> （コードの書き心地はクラス、動く速度は基本型）

---

## 2. 背景：従来のJavaが抱える課題

従来のJavaには、データの扱いにおいて大きな二項対立が存在しました。

| 特徴 | 基本型 (Primitive Types) | 参照型 / オブジェクト (Reference Types) |
| :--- | :--- | :--- |
| **例** | `int`, `double`, `boolean` | `Integer`, `String`, `Point` (カスタムクラス) |
| **メモリ配置** | メモリ（スタック/配列内）に直接値が配置される | ヒープ上にオブジェクトヘッダと共に配置され、変数はポインタ（参照）を保持 |
| **パフォーマンス** | キャッシュ効率が高く非常に高速 | ポインタのたどり（Indirection）やGC負荷、メモリ断片化が発生 |
| **抽象化・拡張性** | メソッドを持てず、ジェネリクス (`List<int>`) に使えない | インターフェース実装やメソッド定義、ジェネリクスに対応 |

### 課題の具体例：メモリの連続性とキャッシュミス
Javaで `Point(int x, int y)` というクラスの配列 `Point[]` を作った場合、配列内には `Point` オブジェクトへの参照（ポインタ）が並び、実際の `Point` オブジェクトはヒープ領域のバラバラな場所に配置されます。
現代のCPUは連続したメモリをまとめてキャッシュ（L1/L2キャッシュ）に読み込むため、ポインタをたどる構造は**キャッシュミスを引き起こし、速度低下の大きな原因**になっていました。

---

## 3. Project Valhalla がもたらす主要な改善

Project Valhalla では主に以下の機能が導入されます。

### ① Value Classes (値クラス / バリューオブジェクト)
- **アイデンティティを持たないクラス**: `==` による参照比較や `synchronize` によるロック、インスタンス識別コードを持たないクラスを定義できます。
- **インライン配置 (Flattening)**: オブジェクトヘッダを排除し、メモリ上に値そのものを隙間なく配置します。これにより `Point[]` 配列は `int` が交互に並ぶだけの連続したメモリ構造となり、`int[]` 同等のメモリ効率と処理速度を実現します。

### ② Universal Generics (汎用ジェネリクス)
- 従来は `List<Integer>` のように参照型しか使えず、基本型を使う場合はボクシング（`int` ⇔ `Integer` の変換コスト）が発生していました。
- Valhalla により、`List<int>` や `List<Point>` のように基本型や値クラスを直接ジェネリクスの型引数として使えるようになります。

### ③ Null制限型 (Null-restricted types)
- `Point!` のように null を許容しない型宣言が可能になります。
- nullチェックのフラグ領域が不要になるため、メモリレイアウトの最適化が極限まで行われます。

---

## 4. コード例 (イメージ比較)

### 従来 (Java 21 以前)
```java
// オブジェクトヘッダ (12~16バイト) + x (4バイト) + y (4バイト)
// 配列 Point[] は参照の配列となり、ヒープ上に分散
public class Point {
    private final int x;
    private final int y;

    public Point(int x, int y) {
        this.x = x;
        this.y = y;
    }
}
```

### Valhalla 導入後 (イメージ)
```java
// value キーワードを付与 (アイデンティティを持たない)
public value class Point {
    private final int x;
    private final int y;

    public Point(int x, int y) {
        this.x = x;
        this.y = y;
    }
}

// 利用例：List<int> や Point のインライン配列が実現可能
List<Point> points = new ArrayList<>();
Point[] pointArray = new Point[1000]; // メモリ上に 2000 個の int がフラットに連続配置される
```

---

## 5. まとめ・メリット

1. **メモリ消費量の削減**: オブジェクトヘッダのオーバーヘッドがなくなる。
2. **実行速度の劇的向上**: CPUキャッシュの有効活用とボクシング処理の撤廃。
3. **コードの可読性・メンテナンス性向上**: クラスによるカプセル化やメソッド定義を維持したまま、最高レベルのパフォーマンスが得られる。

---

## 6. コードの書き方はどう変わるか？ (書き方と互換性)

### ① 既存コードとの完全な後方互換性
既存のJavaコード（`class` や `List<Integer>` など）は**書き直さなくてもそのまま動作します**。Valhallaの新しい書き方は「opt-in（明示的に選択して使う）」スタイルです。

### ② 新しく追加される書き方・キーワード

#### 1. `value class` (バリュークラス)
クラス定義に `value` 修飾子を付与します。

```java
// value キーワードをつけるだけ（記述感は通常のクラスや Record とほぼ同じ）
public value class Color {
    private final int r;
    private final int g;
    private final int b;

    public Color(int r, int g, int b) {
        this.r = r;
        this.g = g;
        this.b = b;
    }

    public int getLuminance() {
        return (r + g + b) / 3;
    }
}
```
※ Record構文と組み合わせることも可能です： `public value record Point(int x, int y) {}`

#### 2. 基本型ジェネリクス (`List<int>`)
ボクシング用クラス (`Integer`) ではなく、直接 `int` やバリュークラスを渡せるようになります。

```java
// 従来：List<Integer> list = new ArrayList<>(); (ボクシング発生)
// 今後：
List<int> intList = new ArrayList<>();
List<Point> pointList = new ArrayList<>();
```

#### 3. Null制限型 (`Point!` / `Point?`)
メモリ空間をさらに最適化するため、nullを許容するかどうかを明示できるようになります。

```java
Point! nonNullPoint; // null を許容しない（デフォルト値は初期化値）
Point? nullablePoint; // null を許容する
```

### ③ 制約事項（注意点）
`value class` に指定したクラスでは、**「オブジェクトの同一性（Identity）」に依存する操作が禁止/制限**されます。
- `synchronized(obj)` によるロックの禁止
- `==` による「参照が同じか」の判定（`==` は「値が全フィールド一致するか」の比較になる）
- フィールドの変更（原則としてすべてのフィールドが `final` で非変/Immutableになる）

