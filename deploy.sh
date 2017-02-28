#!/bin/bash

TELEGRAM_DEFAULT_PATH=/opt/
TELEGRAM_DEFAULT_FOLDER_NAMES=(
  "telegram"
  "telegram-cli"
  "tg"
)

if [ -d ${TELEGRAM_DEFAULT_PATH} ]; then
  for folder_name in ${TELEGRAM_DEFAULT_FOLDER_NAMES[@]}; do
    if [ -d "${TELEGRAM_DEFAULT_PATH}/${folder_name}" ]; then
      TELEGRAM_ROOT="${TELEGRAM_DEFAULT_PATH}/${folder_name}"
      break
    fi
  done
fi

if [ ! -z ${TELEGRAM_ROOT} ]; then
  echo "Telegram-CLI root folder not found."
  read -p "Please, write its path: " TELEGRAM_ROOT
  if [ ! -d ${TELEGRAM_ROOT} ]; then
    echo "Still not found. Exiting."
    exit 1
  fi
fi

TELEGRAM_BINARY="${TELEGRAM_ROOT}/bin/telegram-cli"

if [ ! -e ${TELEGRAM_BINARY} ]; then
  echo "Telegram-CLI main binary not found."
  echo "Are you sure you compiled everything?"
  echo "If help is needed, point to: https://github.com/vysheng/tg"
  exit 1
fi

echo "Before starting, an information from your Nagios instance."
read -p "Nagios command file path [/var/spool/nagios/cmd/nagios.cmd]: " NAGIOS_COMMAND_FILE
if [ "$(echo ${NAGIOS_COMMAND_FILE})" == "" ]; then
  NAGIOS_COMMAND_FILE=/var/spool/nagios/cmd/nagios.cmd
fi
TELEGRAM_ETC="/etc/telegram-cli"
TELEGRAM_SPOOL="/var/spool/telegramd"

mkdir -p ${TELEGRAM_ETC}
mkdir -p ${TELEGRAM_SPOOL}
cp -f "${TELEGRAM_ROOT}/tg-server.pub" "${TELEGRAM_ETC}/"
sed -i "/^TELEGRAM_CLI=/c TELEGRAM_CLI=${TELEGRAM_BINARY}" ./src/telegramd
sed -i "/^NAGIOS_COMMAND_FILE\ =\ /c NAGIOS_COMMAND_FILE\ =\ ${NAGIOS_COMMAND_FILE}" ./src/cmd_interface.py
cp -f ./src/cmd_interface.py ${TELEGRAM_ROOT}/cmd_interface.py

# README: this part is extremely linked to the running distribution
cp -f ./src/telegramd /etc/rc.d/init.d/
for index in {0..6}; do
  cd /etc/rc.d/rc${index}.d/
  ln -s ../init.d/telegramd S80telegramd
done
service telegramd start
