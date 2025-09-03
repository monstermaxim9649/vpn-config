# update_xray.sh  
#!/bin/bash
echo "Обновление Xray..."
docker-compose restart xray-reality
sleep 3
echo "Статус:"
docker ps | grep xray-reality
