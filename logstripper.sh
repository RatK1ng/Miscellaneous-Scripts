for file in ./*
do
printf "\n\n"
echo $file
grep -c '<?xml version="1.0" encoding="UTF-8"?>' $file
grep -Po '([0-9]{4}-[0-9]{2}-[0-9]{2}[A-Z][0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z<\/env)' $file|head -1|sed 's/.....$//'
grep -Po '([0-9]{4}-[0-9]{2}-[0-9]{2}[A-Z][0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z<\/env)' $file|tail -1|sed 's/.....$//'
done
