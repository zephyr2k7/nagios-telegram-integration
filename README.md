# Logic

_nagios-telegram-integration_ is a set of utilities made for the purpose of obtain a functional integration between _Nagios_ monitoring server and _Telegram_.

Actually, this project was born because of the needs of having _Nagios_ alarms notifications more quickly and in a place with easier - and initially basilar - interaction.

**N.B.** Our _Nagios_ infrastructure involves the use of _NagiosQL_.

## Preliminary activity

First of all we needed to get _Telegram-CLI_ and configure it. Just pull down _vysheng_'s code and compile as he perfectly describes in his in the [_README_](https://github.com/vysheng/tg).

We opted to make _Telegram-CLI_ run as a unit service, listening for commands on a UNIX socket.

## Receiving notifications via _Telegram_

First step has been configuring everything to make _Nagios_ use also _Telegram_ channel to notify any alarm: as every other contact channel, we need a command to send messages with.

For **hosts** alarms:

```
/usr/lib/nagios/plugins/send_telegram_msg "$CONTACTADDRESS1$" "$NOTIFICATIONTYPE$ for $HOSTALIAS$: $HOSTSTATE$ (info: http://nagios.corp.net/cgi-bin//status.cgi?host=$HOSTNAME$)"
```

For **services** alarms:

```
/usr/lib/nagios/plugins/send_telegram_msg "$CONTACTADDRESS1$" "$NOTIFICATIONTYPE$ for $HOSTALIAS$: $SERVICEDESC$ is $SERVICESTATE$ (info: http://nagios.corp.net/cgi-bin//status.cgi?host=$HOSTNAME$)"
```

You should notice two important things:

1. **send_telegram_msg** plugin. It's not a real plugin, it's just a script that _pipes_ messages into the UNIX socket of _Telegram-CLI_ running instance, resolving them with the correct _Telegram-CLI_ syntax.
2. **$CONTACTADDRESS1$** parameter. Yup, we use _$CONTACTADDRESS1$_ to identify every contact user. So, every user configured on _Nagios_ has the _$CONTACTADDRESS1$_ valorized with the _Telegram-CLI_ peer name (when contacts get added into _Telegram-CLI_ a peer name is automatically generated. You can also rename it.).

## Sending acknowledgements via _Telegram_

Don't worry. I will write this section too. Sooner or later.

### Yeah, I know. Lot of things still missing. Give me few days and you'll have this repo ready
