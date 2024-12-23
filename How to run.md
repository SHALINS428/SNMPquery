## 配置详细说明：

#### 安装相关的软件：
1. Docker-desktop.
2. VS-code
3. sqllite
3. 在VS-code的终端中安装相关的依赖：
    ```
    pip install pysnmp==4.4.12 time PyQt5 matplotlib
    ```

---

#### Docker相关命令： 
1. 创建 Docker 网络
        ```docker network create --subnet=172.19.16.0/24 shalins```
2. 检查网络是否创建成功：
        ```docker network ls```
3. 验证网络详细信息：
        ```docker network inspect shalins```
4. 修改docker Engine的内容如下：
    ```
    {
    "bridge": "docker0",
    "builder": {
        "gc": {
        "defaultKeepStorage": "20GB",
        "enabled": true
        }
    },
    "dns": [
        "8.8.8.8",
        "8.8.4.4"
    ],
    "experimental": false,
    "iptables": true,
    "registry-mirrors": [
        "https://registry.docker-cn.com",
        "https://mirror.ccs.tencentyun.com",
        "https://docker.mirrors.ustc.edu.cn"
    ]
    }
    ```

5. 创建 SNMP Docker 镜像

    1. 在本地创建一个名为 Dockerfile 的文件,内容如下
        ```
        FROM alpine:latest
        RUN apk add --no-cache net-snmp net-snmp-tools
        COPY snmpd.conf /etc/snmp/snmpd.conf
        CMD ["/usr/sbin/snmpd", "-f", "-Lo"]
        ```
    2. 配置snmpd.conf:
        ```
        rocommunity public
        syslocation Docdker-Lab
        syscontact admin@docker.local
        sysName SNMP-Test
        ```
    3. 使用以下命令构建镜像:
        ```docker build -t custom-snmpd .```
        

6. Docker容器相关操作·：

    1. 运行以下命令，创建 60 台主机容器，并分配固定 IP 地址，**同时实现了端口映射**：
        ```FOR /L %i IN (1,1,60) DO docker run -d --net shalins --ip 172.19.16.%i -p 161%i:161/udp --name snmp%i custom-snmpd```
    2. 开启容器：
        ```FOR /L %i IN (1,1,60) DO docker start snmp%i```
    3. 关闭容器：
       ``` FOR /L %i IN (1,1,60) DO docker stop snmp%i```
    4. 一次性启动所有包含 snmp 的容器；
        ```FOR /F "tokens=*" %i IN ('docker ps -a -q --filter "name=snmp"') DO docker start %i```
    5. 一次性停止所有包含 snmp 的容器
        `FOR /F "tokens=*" %i IN ('docker ps -q --filter "name=snmp"') DO docker stop %i`

7. 如何启动完整的环境
    在完成容器的创建后，启动所有容器
    
    在VS-code中运行query.py
    选择功能一可以实现在终端中输出通过snmp查询到的容器信息。
    选择功能二可以实现对每一个所选择的容器的接受和转发数据的字节数

    在VS-code中运行test.py可以实现对query.py中功能一的图形化界面。**并且实现了自动更新**
8. 人为制造snmp流量
    snmpwalk -v 2c -c public 172.19.16.45:161 1.3.6.1.2.1.2.2.1.10
## 系统特点说明

1. 由于对于环境中的每个设备，我们仅需要其与SNMP协议有关的功能。所以本项目使用docker而非虚拟机作为模拟60个主机的环境。
2. 通过对docker容器进行端口映射，在程序中监察本地端口，来实现信息的交互。简化了对数据进行可视化的操作。
3. 使用linux作为docker容器的操作系统类型。防止了在windows系统中安装Snmp-net的复杂操作。
4. 使用sqllite作为数据的存储方式。相比于完整的数据库更轻便。
5. 在实现数据库和图形化界面的定时更新时，使用了python的多线程实现。防止在单线程情况下，后台调用更新函数会阻塞前台服务。这将会引起程序崩溃。