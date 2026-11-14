# Changelog

## [1.2.0](https://github.com/echohello-dev/wingman/compare/v1.1.0...v1.2.0) (2026-11-14)


### Features

* **api:** add conversation list and detail endpoints with pagination ([#18](https://github.com/echohello-dev/wingman/issues/18)) ([7a67570](https://github.com/echohello-dev/wingman/commit/7a67570726a1c24080d4ed2838c206048cbdb1fb))
* **api:** add paginated document list and detail endpoints ([#22](https://github.com/echohello-dev/wingman/issues/22)) ([8b76f58](https://github.com/echohello-dev/wingman/commit/8b76f58429670e2bc660796343ef2bcbf3a8d380))
* **api:** preview retrieved chunks and distances ([#42](https://github.com/echohello-dev/wingman/issues/42)) ([7c40888](https://github.com/echohello-dev/wingman/commit/7c40888bd3868a7b28adc6f275edacc0452668cd))
* **logging:** add structured wide-event logging baseline ([#11](https://github.com/echohello-dev/wingman/issues/11)) ([6d8d923](https://github.com/echohello-dev/wingman/commit/6d8d92399ae9e832dea4b7cf653f1d3a98180087))
* **rag:** add optional retrieval distance cutoff ([#30](https://github.com/echohello-dev/wingman/issues/30)) ([cec442a](https://github.com/echohello-dev/wingman/commit/cec442a266e84f4224db558c868d04aa187369b5))
* **rules:** add keyword-rule matcher with config loading ([#16](https://github.com/echohello-dev/wingman/issues/16)) ([dc7dfed](https://github.com/echohello-dev/wingman/commit/dc7dfed3fd7690b8c70a6be7a5c787c8b1bae240))
* **rules:** honour operator rules on the Slack submit path ([#20](https://github.com/echohello-dev/wingman/issues/20)) ([e7789f6](https://github.com/echohello-dev/wingman/commit/e7789f63e7a4acada904d0a2c18ebee64769eaa8))
* run Wingman agents on Pi Durable ([#14](https://github.com/echohello-dev/wingman/issues/14)) ([d078bd2](https://github.com/echohello-dev/wingman/commit/d078bd2e6ba32529363b5fa483f59d2dc5af8fda))


### Bug Fixes

* **api:** include saved roots when indexing Slack threads ([#38](https://github.com/echohello-dev/wingman/issues/38)) ([df3001a](https://github.com/echohello-dev/wingman/commit/df3001a30691c7ec7c1e51d1ce1f2a98da2452d3))
* **api:** keep conversation previews within channel scope ([#34](https://github.com/echohello-dev/wingman/issues/34)) ([1d5344c](https://github.com/echohello-dev/wingman/commit/1d5344cfa879c91baf87a3df49260b85e9aca71b))
* **api:** reject blank document fields before indexing ([#46](https://github.com/echohello-dev/wingman/issues/46)) ([5e381ff](https://github.com/echohello-dev/wingman/commit/5e381ff78e8f334747b65bf98da20d139681e628))
* **rag:** allow indexing into an empty Chroma collection ([#28](https://github.com/echohello-dev/wingman/issues/28)) ([26f9f91](https://github.com/echohello-dev/wingman/commit/26f9f9117a56d3fd96eaf4432f57b86605955d8e))
* **rag:** apply channel scope before retrieval limit ([#27](https://github.com/echohello-dev/wingman/issues/27)) ([85e1f8d](https://github.com/echohello-dev/wingman/commit/85e1f8df68e32d22a7eb5f3d4572b06844d3ba53))
* **rag:** make Slack thread re-indexing idempotent ([#36](https://github.com/echohello-dev/wingman/issues/36)) ([f525c9e](https://github.com/echohello-dev/wingman/commit/f525c9e1e31a41b4036b81a2f4565cb9593e5442))
* **rag:** validate chunk settings and stop redundant tail fragments ([#40](https://github.com/echohello-dev/wingman/issues/40)) ([85c83ff](https://github.com/echohello-dev/wingman/commit/85c83ff306fba821839f7dbd0568f5f5a6aef436))

## [1.1.0](https://github.com/echohello-dev/wingman/compare/v1.0.0...v1.1.0) (2026-07-24)


### Features

* **bot:** add AI streaming with thinking steps ([3298c02](https://github.com/echohello-dev/wingman/commit/3298c02824a468136bb5e76cdd0126bad951a7de))
* **conversation:** implement conversation memory and history storage ([40cb95f](https://github.com/echohello-dev/wingman/commit/40cb95ff0e1f99e097b2cabcb863fab14193584b))
* enhance VSCode configuration and update Slack message posting ([c7d8e0c](https://github.com/echohello-dev/wingman/commit/c7d8e0cfaefb8f9f7f168e431667d8146262b878))
* **migrations:** add initial schema with conversation memory and related tables ([bd851ff](https://github.com/echohello-dev/wingman/commit/bd851ff65e2afa85ae360bf187f6e9cca8b5e41f))


### Bug Fixes

* **config:** make Slack credentials optional with defaults for testing ([0a6a71a](https://github.com/echohello-dev/wingman/commit/0a6a71aa164ccefc53ae438411e7532c6e511b02))
* update Dockerfiles to match project tooling ([1ef2d4e](https://github.com/echohello-dev/wingman/commit/1ef2d4ecbfb568e885af77def134f3f4657018b1))
* upgrade Python 3.13 and update dependencies for Pydantic 2.x compatibility ([e14d51c](https://github.com/echohello-dev/wingman/commit/e14d51cba53458d87f6b75e2f18ee928cefab44f))
