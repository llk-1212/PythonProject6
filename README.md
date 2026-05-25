# PythonProject6
scrapy分布式爬取https://books.toscrape.com/的书籍信息，爬取github项目，爬取阿里公益项目


## 功能特性
- 爬取https://books.toscrape.com/的全部书籍信息并存储到Redis中
- 爬取github上开发语言为"python", "java", "javascript", "go","rust", "typescript", "c++", "c#"的前三页项目，并利用JSON解析http响应存储到Redis中
- 爬取阿里公益项目存储到MongoDB中
- 实时监控爬虫进度
- 将数据库中的数据导出成json或者csv格式

## 快速开始
​```bash
git clone https://github.com/llk-1212/PythonProject6.git
cd PythonProject6
npm install
npm start
​```

## 使用示例
运行book_spider/github_spider需要先注释中间件中的Selenium,数据管道中的MongoDB
<img width="1130" height="829" alt="image" src="https://github.com/user-attachments/assets/6dd0e46f-dc2b-403c-a985-a38ec4756d49" />
<img width="1391" height="943" alt="image" src="https://github.com/user-attachments/assets/827fa3e9-773e-430d-a373-87e659b2abae" />
<img width="1209" height="934" alt="image" src="https://github.com/user-attachments/assets/7976c337-b2f6-47bd-b7bf-f56266c28cb4" />
<img width="1471" height="1004" alt="image" src="https://github.com/user-attachments/assets/2b8e452d-4a8e-414c-a463-1acd9f170393" />






