Ошибка при сборке:
```bash
Error response from daemon: Ports are not available: exposing port TCP 0.0.0.0:8514 -> 0.0.0.0:0: listen tcp4 0.0.0.0:8514: bind: An attempt was made to access a socket in a way forbidden by its access permissions.
```

Посмотреть диапазон динамических портов
```powershell
netsh int ipv4 show dynamicport tcp
```
Заменить динамический диапазон
```powershell
netsh int ipv4 show dynamicport tcp
```