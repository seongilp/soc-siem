FROM debian:12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-server rsyslog nginx-light \
 && rm -rf /var/lib/apt/lists/* \
 && mkdir -p /run/sshd

# 랩 전용 계정. 공격 시나리오의 워드리스트에 들어 있는 약한 비밀번호를 일부러 쓴다.
ARG LAB_USER=labuser
ARG LAB_PASSWORD=summer2026
RUN useradd -m -s /bin/bash "$LAB_USER" \
 && echo "$LAB_USER:$LAB_PASSWORD" | chpasswd \
 && printf 'PasswordAuthentication yes\nPermitRootLogin no\nMaxAuthTries 6\nLogLevel INFO\n' \
      > /etc/ssh/sshd_config.d/lab.conf

COPY rsyslog.conf /etc/rsyslog.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && echo '<h1>soc-siem lab target</h1>' > /var/www/html/index.html

EXPOSE 22 80
ENTRYPOINT ["/entrypoint.sh"]
