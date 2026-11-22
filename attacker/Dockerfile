FROM alpine:3.20
RUN apk add --no-cache hydra openssh-client sshpass curl
COPY users.txt passwords.txt /opt/lab/
COPY attack.sh /usr/local/bin/attack
RUN chmod +x /usr/local/bin/attack
ENTRYPOINT ["attack"]
CMD ["all"]
