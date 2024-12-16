1. 创建 Docker 网络

    1. 创建 Docker 网络
        docker network create --subnet=172.19.16.0/24 shalins
    2. 检查网络是否创建成功：
        docker network ls
    3. 验证网络详细信息：
        docker network inspect shalins
2. 修改docker Engine的内容如下：
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

3. 创建 SNMP Docker 镜像

    1. 在本地创建一个名为 Dockerfile 的文件,内容如下
        ```
        FROM alpine:latest
        RUN apk add --no-cache net-snmp net-snmp-tools
        COPY snmpd.conf /etc/snmp/snmpd.conf
        CMD ["/usr/sbin/snmpd", "-f", "-Lo"]
        ```
    2. 配置snmp.conf:
        ```
        rocommunity public
        syslocation Docker-Lab
        syscontact admin@docker.local
        sysName SNMP-Test
        ```
    3. 使用以下命令构建镜像:
        docker build -t custom-snmpd .
        

4. Docker容器相关操作·：

    1. 运行以下命令，创建 10 台主机容器，并分配固定 IP 地址：
        FOR /L %i IN (1,1,60) DO docker run -d --net shalins --ip 172.19.16.%i -p 161%i:161/udp --name snmp%i custom-snmpd
    2. 开启容器：
        FOR /L %i IN (1,1,70) DO docker start snmp%i
    3. 关闭容器：
        FOR /L %i IN (1,1,70) DO docker stop snmp%i
    4. 一次性启动所有包含 snmp 的容器；
        FOR /F "tokens=*" %i IN ('docker ps -a -q --filter "name=snmp"') DO docker start %i
    5. 一次性停止所有包含 snmp 的容器
        FOR /F "tokens=*" %i IN ('docker ps -q --filter "name=snmp"') DO docker stop %i

5. 主机所需配置：
    1. 安装 pysnmp
        pip install pysnmp==4.4.12
    2. 安装 PyQt5
        pip install PyQt5
    3. 安装 Matplotlib
        pip install matplotlib




