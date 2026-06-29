# 解决支持FTP共享MLST以及NLST命令带通配符无法正确返回的问题

- step1：  
  原始需求分解分配  
  输出测试需求清单
  
    - 产品原始需求
      
        - 原始需求按统一粒度分解  
          输出测试需求
          
    - 测试经验库
      
        - 直接提取测试需求
          
    - 用户需求(含隐含需求)
      
        - 直接提取测试需求
          
    - 客户应用场景分析
      
        - 典型客户应用场景
          
        - 隐含客户需求
          
    - 产品继承性分析
      
        - 质量成熟度分析
          
          > 经过测试的版本数、网上应用情况反馈  
            - 新增测试策略建议
              
        - 失效影响度分析
          
          > 特性使用频度、特性重要性  
            - 新增测试策略建议
              
        - 下游漏测/历史测试bug分析
          
            - 新增测试需求
              
    - 协议/规范
      
        - 直接提取测试需求
          
- step2：  
  基于测试需求清单  
  输出测试用例设计
  
    - 测试类型分析
      
        - 功能测试
          
            - FTP共享NLST命令（匹配文件混合三种编码）
              
                - 前提中文占一个字符
                  
                - *  任意长度字符匹配
                  
                  > （支持使用*匹配任意长度的字符序列（包含空字符串)，支持中文字符）  
                  >   
                    - 无子目录
                      
                        - 工作目录下有 test.txt（UTF-8）、test1.txt（GBK）、test_中文.txt（Big5）、test_中 文.txt、test_中文%$.txt
                          
                            - NLST *.txt
                              
                    - 子目录
                      
                        - subdir/目录下有 test.txt、test1.txt、test_中文.txt、test_中 文.txt、test_中文%$.txt
                          
                            - nlst subdir/*.txt
                              
                                -  test.txt、test1.txt、test_中文.txt、test_中 文.txt、test_中文%$.txt
                                  
                - 单字符 ? 匹配（中文字符个数1个 ）
                  
                    - 目录含 a.txt、ab.txt、1.txt、test中.log、ab\.txt、test中\.log
                      
                        - 发送 nlst ?.txt
                          
                            - a.txt、1.txt
                              
                        - 发送 nlst ?b.txt
                          
                            - ab.txt
                              
                        - 发送nlst ??\.txt（\ 为转义）
                          
                            -  ab.txt、ab\.txt
                              
                        - 发送nlst ?????\.txt
                          
                            - 为空
                              
                        - 发送nlst ?????\.log
                          
                            - test中.log、test中\.log
                              
                - 字符集合匹配[]，仅匹配单个字符
                  
                    - 目录含 a.txt、testa.txt、test1.txt、test123.txt、test中123.txt、test中.txt、**testAB.txt**、testZ.txt、testz.txt
                      
                        - ①用于匹配集合中任意一个字符，如：
                          
                            - 发送nlst test[abc].txt
                              
                                - testa.txt
                                  
                            - 发送nlst test[123中].txt
                              
                                - test1.txt  
                                  test2.txt  
                                  test中.txt  
                                  test3.txt  
                                  
                                  
                        - ②用于匹配指定范围内的字符，如:
                          
                            - 发送nlst test[0-9].txt
                              
                                - test1.txt
                                  
                            - 发送nlst test[a-z].txt
                              
                                - testa.txt
                                  
                            - 发送nlst test[A-Z].txt
                              
                                - testZ.txt
                                  
                            - 发送nlst test[a-Z].txt
                              
                                - testZ.txt、testz.txt、testa.txt
                                  
                        - ③用于匹配不属于集合范围的字符，如：
                          
                            - 发送nlst test[!0-9].txt
                              
                                - testa.txt  
                                  test中.txt  
                                  testZ.txt  
                                  testz.txt
                                  
                - 支持在同一路径参数中组合使用*、？、[]等通配符
                  
                    - 目录 subdir/ 包含 abx.txt、aba.txt、a.txt、abc.log、中文一二.txt
                      
                        - 发送发送nlst subdir/??*[!a]*.txt*
                          
                            - abx.txt、中文一.txt、中文一二.txt
                              
                        - nlst subdir/??*[一]?.txt    ***nlst subdir/??*****[!a][二].txt***
                          
                            - 中文一二.txt
                              
                        - **nlst subdir/??*****[!a][一].txt***
                          
                            - 空
                              
                        - **nlst subdir/??*****[!a][二]?.txt***
                          
                            - 返回空
                              
                - 递归与跨目录
                  
                    - dir1/和dir2/是同级， 各有文件
                      
                        - NLST dir1/../dir2/*.txt
                          
                            - 返回 dir2 中的匹配项
                              
                    - dir1/dir2...../dir10,嵌套目录上限，以系统限制为准
                      
                        - NLST dir1/../dir10/*.txt
                          
                            - 返回 dir10中的匹配项
                              
                - 非法模式
                  
                    - NLST test[.txt
                      
                    - NLST [!
                      
                - NLST不带参数
                  
                    - 仅返回文件名列表
                      
                - 大量文件性能
                  
                    - 目录下生成 100 、200 、 500、1000w个 .log 文件（用于推测更大量文件相应时间）
                      
                        - NLST *.log 并记录响应时间
                          
                            - 在可接受时间（待定）内完成？，且结果完整
                              
                                - 分钟级别
                                  
            - FTP共享MLST命令
              
                - 通配符开关，默认关闭 
                  
                    - 存在的目录/文件
                      
                        -  MLST 单文件
                          
                            - 获取单个文件的详细属性信息
                              
                        -  MLST 目录或嵌套目录（层级是否有上限）
                          
                            - 获取单个目录的详细属性信息
                              
                    - 不存在的目录/文件
                      
                        - MLST 不存在的文件.txt
                          
                            - （服务器返回“550 对象不存在”）
                              
                        - MLST 不存在的目录
                          
                            - （服务器返回“550 对象不存在”）
                              
                - 通配符开启 ，返回命中的第一个结果
                  
                    - 复用nlst  * ？[]  混合三种通配符测试点
                      
                    - 非法模式/不带参数
                      
                    - 大量文件性能
                      
            - **多客户端并发执行**
              
                - 模拟多个客户端同时执行 NLST *或 MLST 文件名，验证服务器是否能稳定响应，无崩溃或数据错乱。（小规模）
                  
- step3：  
  测试策略
  
    - 基于风险分析，识别测试优先级
      
        - 测试重点：关键交付功能/场景等
          
        - 测试难点：高风险模块
          
    - 测试资源(可选)
      
        - 特殊物料识别：arm服务器等
          
        - 提前测试资源准备：预埋数据等
          
    - 专项测试规划
      
        - 长稳测试商用指标(可选)
          
        - 性能测试商用指标(可选)
          
    - 自动化目标制定
      
        - 是否合入冒烟：涉及io主流程须合入
          
        - 建议自动化覆盖点
          
