# コードレビュー結果と対応状況

> 更新日: 2026-08-10

## 完了した対応

| 分類 | 対応 |
| --- | --- |
| WIF | 共有 SA を Terraform PR plan、Terraform main apply、docs 公開の 3 ID に分離 |
| 信頼条件 | repository ID、branch / PR ref、固定 workflow reference に限定 |
| IAM | 旧共有 SA の project IAM admin、WIF admin、SA admin を削除 |
| State | state bucket で Uniform bucket-level access を有効化し、PR plan の object access を state prefix に限定 |
| 配信 | docs SA は対象 bucket にのみ object sync と bucket metadata 読取りを許可 |
| コンテナ | Artifact Registry を削除し、Cloud Run は公式 NGINX の digest 固定イメージを使用 |
| 通信 | Cloud Run は internal LB ingress、HTTP は HTTPS redirect、IAP SA だけが invoke |
| 再現性 | Terraform 1.15.8、Google Provider 7.43.0、Actions SHA pin、`uv.lock` を採用 |

## 運用上の注意

- `bootstrap/` は GCP 管理者だけが実行する。通常の CI/CD に bootstrap 用の権限を与えない。
- `TFVARS_FILE` を更新する場合、`container_image` は SHA-256 digest 固定の形式を維持する。
- state bucket の個人管理者アクセスは bootstrap 作業に必要な場合だけ付与し、不要になれば削除する。
