# OTUServer
The fifth homework

## Описание

Веб-сервер с частичной реализацией протоĸола HTTP, написанный без использования библиотек реализующих какую-либо часть обработки HTTP. Работаем напрямую с сокетами.

## Спецификация

### Структура запуска сервиса

При запуске сервиса из командной строки можно передать два параметра:

|Название|Тип|Описание|Значение по-умолчанию|Аргумент командной строки|
|--------|---|--------|---------------------|-------------------------|
|document_root|string|Адрес директории с которой работает веб-сервер|http-test-suite-master|-r|
|number_workers|int|Число worker'ов|1024|-w|

### Поддержка методов
- HEAD
- GET

### Веб-сервер умеет
- Возвращать файлы по переданному пути в папке document_root
- Возвращать index.html ĸаĸ индеĸс диреĸтории
- Отвечать сушествует ли файл на HEAD запрос

## Результаты нагрузочного тестирования
|Показатель|Значение|
|----------|--------|
|Concurrency Level|100|
|Time taken for tests|18.552 seconds|
|Complete requests|50000|
|Failed requests|0|
|Non-2xx responses|0|
|Total transferred|5500000 bytes|
|HTML transferred|0 bytes|
|Requests per second|2695.17 [#/sec] (mean)|
|Time per request|37.103 [ms] (mean)|
|Time per request|0.371 [ms] (mean, across all concurrent requests)|
|Transfer rate|289.52 [Kbytes/sec] received|

## Запуск сервера

Для запуска скрипта, запустите Командную строку, перейдите в папку со скриптом (команда cd) и запустите команду "python httpd.py" (windows)
