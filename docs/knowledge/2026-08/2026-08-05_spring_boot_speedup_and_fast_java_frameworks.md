# Spring Bootの起動・テスト高速化と代替Javaフレームワーク・テスト手法

本ドキュメントでは、Spring Bootアプリケーションおよびテストの起動速度を向上させる手法と、より高速なJavaフレームワークやテスト関連ライブラリについてまとめる。

---

## 1. Spring Boot アプリケーションの起動高速化

Spring Bootの起動が遅い主な原因は、**JVMのJITコンパイル起動コスト**、**クラスパスのコンポーネントスキャン**、**リフレクションによるAuto-Configuration**、**大量のBeanの初期化**である。

### 1.1 設定・コーディングによる即座に効く高速化

#### ① 遅延初期化（Lazy Initialization）の有効化
開発環境やテスト環境で全Beanを即時生成せず、必要時に生成する。

`application.properties`:
```properties
spring.main.lazy-initialization=true
```

#### ② 不要な Auto-Configuration の除外
使っていないアタッチメント（例: DBを使ってないのにDataSource関連のオートコンフィグが入っている等）を除外する。

```java
@SpringBootApplication(exclude = {
    DataSourceAutoConfiguration.class,
    HibernateJpaAutoConfiguration.class
})
public class Application { ... }
```

#### ③ コンポーネントスキャンの範囲を最小化
`@ComponentScan` でベースパッケージを絞り込み、不要なパッケージのスキャンを防ぐ。

---

### 1.2 JVM・ビルドレベルの起動高速化

#### ① Spring AOT (Ahead-Of-Time) と GraalVM Native Image
Spring Boot 3.x 以降では、GraalVM Native Image サポートが標準化されている。事前コンパイルにより起動時間を **数秒 -> 数十ミリ秒** に短縮できる。

- **長所**: 起動時間が劇的に速い、メモリ使用量が大幅に少ない
- **短所**: ビルド時間が長い、リフレクションや動的バイナリ生成の事前定義が必要

#### ② CRaC (Coordinated Restore at Checkpoint)
ウォームアップ済みのJVMメモリ状態をディスクに保存（CheckPoint）し、次回起動時にその状態から復元（Restore）する技術（OpenJDK CRaC）。

- 起動時間を数十〜数百ミリ秒に短縮可能。
- AWS Lambdaなどのサーバーレス環境で非常に有効。

#### ③ Class Data Sharing (CDS / AppCDS)
JVMのメタデータをあらかじめファイルにキャッシュ（Dump）し、起動時に再利用することでクラスロード時間を短縮する。

```bash
# 1. 起動時にクラス一覧を作成
java -XX:ArchiveClassesAtExit=app-cds.jsa -jar app.jar
# 2. 2回目以降の起動
java -XX:SharedArchiveFile=app-cds.jsa -jar app.jar
```

---

## 2. Spring Boot テストの起動・実行高速化

テストが遅い最大の要因は **`ApplicationContext` の再作成（Re-creation）** である。

### 2.1 Spring Test Context のキャッシュ最大化

Spring Test は、テスト構成（`@SpringBootTest` の設定、`@MockBean` の有無など）が同じであれば `ApplicationContext` を使い回す（キャッシュする）。

- **コンテキスト破棄を避ける**: `@DirtiesContext` の使用は極力避ける（使うとコンテキストが再起動する）。
- **`@MockBean` / `@SpyBean` の定義を共通化**: 異なるテストクラスで個別に `@MockBean` を追加すると、設定が異なるため別の `ApplicationContext` が起動してしまう。ベースクラスを用意するか、共通設定クラスにまとめる。

### 2.2 重い `@SpringBootTest` から軽量テストへの移行

| テスト種別 | 起動コスト | 用途 |
|---|---|---|
| **Plain JUnit (+ Mockito)** | **超高速 (数ミリ秒)** | ビジネスロジック、Domain/Service層の単体テスト |
| **`@WebMvcTest`** | **軽量 (1〜2秒)** | Controller層のWebルーティング・バリデーションテスト |
| **`@DataJpaTest`** | **軽量 (1〜2秒)** | Repository/DBアクセス層のテスト |
| **`@SpringBootTest`** | **重量 (数秒〜十数秒)** | E2E / 結合テストのみに限定 |

```java
// 爆速な純粋単体テスト例 (Spring Contextを起動しない)
@ExtendWith(MockitoExtension.class)
class UserServiceTest {
    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private UserService userService;

    @Test
    void testGetUser() {
        // ...
    }
}
```

### 2.3 JUnit 5 の並列テスト実行

`junit-platform.properties`:
```properties
junit.jupiter.execution.parallel.enabled=true
junit.jupiter.execution.parallel.mode.default=concurrent
```

### 2.4 Testcontainers の Reuse（再利用）設定
統合テストで Docker コンテナを使う場合、テスト実行ごとにコンテナを破棄せず再利用する。

`~/.testcontainers.properties`:
```properties
testcontainers.reuse.enable=true
```

---

## 3. 高速な代替 Java Web フレームワーク

Spring Boot の代替として、起動速度・メモリ効率・処理パフォーマンスに特化したモダンJavaフレームワークが存在する。

| フレームワーク | 特徴 | 主な用途 |
|---|---|---|
| **Quarkus** | Red Hat開発。"Supersonic Subatomic Java"。GraalVM Native前提で設計されており、**起動数ミリ秒・低メモリ消費**。Dev Services（Docker自動起動）など開発体験も最高水準。 | クラウドネイティブ、Serverless、Microservices |
| **Micronaut** | リフレクションを排し、事前コンパイル(AOT)でDIやアスペクトを実行。メモリが小さく起動が爆速。 | マイクロサービス、サーバーレス |
| **Helidon (Helidon 4)** | Oracle開発。Java 21の **Virtual Threads (Project Loom)** をフル活用した設計(Helidon Níma)。同期コードの書きやすさと非同期の高速性を両立。 | 高並列・高スループットAPI |
| **Javalin** | Sinatraライクな超軽量Webフレームワーク。IoCコンテナなし。学習コストが低く即座に起動する。 | 小規模API、軽量ツール |

---

## 4. 高速なテスト用ライブラリ・ツール

テストコードの作成・実行効率を跳ね上げるライブラリ。

1. **Mockito / MockK** (モックライブラリ)
   - Spring Context を起動せず、高速に依存コンポーネントをモック化。
2. **Instancio** (テストデータ生成)
   - リフレクションを用いて複雑なオブジェクト構造を1行でランダム生成するライブラリ。テストの記述速度と実行速度を両立。
   ```java
   Person person = Instancio.create(Person.class);
   ```
3. **AssertJ** (流暢なアサーション)
   - 型安全かつ高速な検証コードの記述が可能。
4. **ArchUnit** (アーキテクチャ・依存関係検証)
   - SpringContextを立ち上げずに、クラス構造やアノテーションの付与漏れを高速に静的検証する。

---

## 5. コンパイル・ビルド自体の高速化手法

Java / Spring Boot プロジェクトで、`mvn compile` や `./gradlew build` などのビルド・コンパイル処理そのものを高速化する手法。

### 5.1 Gradle / Maven のビルド設定最適化

#### ① Gradle の高速化設定 (`gradle.properties`)
Gradle はデフォルトでも高速だが、以下の設定でさらに高速化できる。

```properties
# Daemonの常駐化 (次回以降のビルドJVM起動コスト削減)
org.gradle.daemon=true

# マルチプロジェクトの並列ビルド
org.gradle.parallel=true

# ビルドキャッシュの有効化 (変更のないタスク入出力をスキップ)
org.gradle.caching=true

# Configuration Cache の有効化 (ビルド構成フェーズの再利用)
org.gradle.unsafe.configuration-cache=true

# Gradle Daemon へのヒープ割り当て拡大
org.gradle.jvmargs=-Xmx4g -XX:+UseG1GC
```

#### ② Maven の並列ビルド & Maven Daemon (`mvnd`)
Maven はデフォルトで単一スレッド実行のため、複数コアを活用する設定を行う。

```bash
# 1. マルチコア並列ビルド (CPUコア数に応じてスレッド数を割り当てる)
mvn clean install -T 1C   # 1コアあたり1スレッド
# または
mvn clean install -T 4    # 4スレッド固定

# 2. Maven Daemon (mvnd) の導入
# Gradle DaemonのようにバックグラウンドでDaemonが常駐し、ビルド時間を大幅削減するツール
mvnd clean package
```

---

### 5.2 IDE (IntelliJ IDEA) でのコンパイル高速化

IDE上のビルド・実行のトリガーを Gradle / Maven 経由ではなく、**IntelliJ の内蔵コンパイラ** に切り替えることで開発時の試行錯誤ループを劇的に短縮できる。

- **IntelliJ IDEA の設定**:
  `Preferences` -> `Build, Execution, Deployment` -> `Build Tools` -> `Gradle`
  - `Build and run using`: `IntelliJ IDEA`
  - `Run tests using`: `IntelliJ IDEA`

これにより、コード変更時の増分コンパイル・起動が1秒未満で行えるようになる。

---

### 5.3 アノテーションプロセッサの最適化

Lombok、MapStruct、Spring Boot Configuration Annotation Processor などのコード自動生成ツールは、コンパイル時間を延ばす一因となる。

- **増分コンパイル（Incremental Annotation Processing）の有効化**:
  最新バージョンの Lombok や MapStruct を利用し、増分コンパイルに対応させる。
- **不必要なアノテーションプロセッサの削除**:
  開発中のみ必要なプロセッサや、代替可能なライブラリを精査する。

---

### 5.4 Docker / CI環境のビルドキャッシュ

CI/CD パイプラインでのビルド時間を短縮する。

- **依存関係レイヤーのキャッシュ**:
  `pom.xml` や `build.gradle` だけを先にコピーして `mvn dependency:go-offline` や `./gradlew dependencies` を実行し、依存JARのダウンロード結果をDockerレイヤーキャッシュやCIキャッシュ（GitHub Actions Cache）に保存する。
- **Spring Boot Layered jar**:
  Spring Boot 2.3+ の `bootBuildImage` や Layered jar 機能を用いて、依存ライブラリとアプリケーションコードのレイヤーを分離し、コンパイル・ビルド後のコンテナイメージ作成を最適化する。

