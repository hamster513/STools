"""
Роуты для работы с архивами баз данных
"""
import traceback
import zipfile
import io
import gzip
import json
import csv
from typing import Dict
from fastapi import APIRouter, HTTPException, UploadFile, File
from datetime import datetime

from database import get_db
from routes.cve import parse_cve_json
from services.metasploit_service import MetasploitService

router = APIRouter()

# Инициализация сервиса Metasploit
metasploit_service = MetasploitService()


def parse_date(date_str):
    """Парсинг даты для ExploitDB"""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return None


@router.post("/api/archive/upload")
async def upload_archive(file: UploadFile = File(...)):
    """Загрузить архив с базами данных"""
    try:
        if not file.filename.endswith('.zip'):
            raise HTTPException(status_code=400, detail="Поддерживаются только ZIP архивы")
        
        print(f"📦 Получен архив: {file.filename}")
        
        # Читаем ZIP архив
        content = await file.read()
        zip_file = zipfile.ZipFile(io.BytesIO(content))
        
        # Получаем список файлов в архиве
        file_list = zip_file.namelist()
        print(f"📋 Файлов в архиве: {len(file_list)}")
        
        results = {
            "epss": {"success": False, "count": 0, "message": ""},
            "exploitdb": {"success": False, "count": 0, "message": ""},
            "metasploit": {"success": False, "count": 0, "message": ""},
            "cve": {"success": False, "count": 0, "message": ""}
        }
        
        db = get_db()
        
        # Обрабатываем каждый файл в архиве
        for file_path in file_list:
            # Пропускаем директории и системные файлы
            if file_path.endswith('/') or '/__MACOSX/' in file_path or file_path.startswith('.'):
                continue
            
            print(f"🔍 Обработка файла: {file_path}")
            
            try:
                # EPSS
                if 'epss' in file_path.lower() and file_path.endswith('.csv.gz'):
                    print(f"📊 Загрузка EPSS: {file_path}")
                    
                    # Распаковываем gzip
                    gz_content = zip_file.read(file_path)
                    print(f"📦 Размер сжатого EPSS файла: {len(gz_content)} байт")
                    
                    with gzip.GzipFile(fileobj=io.BytesIO(gz_content)) as gz:
                        csv_content = gz.read().decode('utf-8-sig')
                    
                    print(f"📄 Размер распакованного EPSS: {len(csv_content)} символов")
                    
                    # Парсим CSV
                    lines = csv_content.splitlines()
                    print(f"📋 Строк в EPSS файле: {len(lines)}")
                    
                    # Показываем первые 3 строки для отладки
                    if len(lines) > 0:
                        print(f"📝 Первая строка (заголовок): {lines[0][:200]}")
                    if len(lines) > 1:
                        print(f"📝 Вторая строка (данные): {lines[1][:200]}")
                    
                    reader = csv.DictReader(lines, delimiter=',')
                    
                    records = []
                    skipped = 0
                    for row in reader:
                        try:
                            cve = row.get('cve', '').strip()
                            epss = row.get('epss', '').strip()
                            
                            if cve and epss:
                                try:
                                    epss_value = float(epss)
                                    records.append({
                                        'cve': cve,
                                        'epss': epss_value
                                    })
                                except ValueError:
                                    skipped += 1
                                    continue
                        except Exception:
                            skipped += 1
                            continue
                    
                    print(f"📊 Обработано записей EPSS: {len(records)}, пропущено: {skipped}")
                    
                    # Сохраняем в базу
                    if records:
                        await db.epss.insert_records(records)
                        results["epss"] = {
                            "success": True,
                            "count": len(records),
                            "message": f"EPSS данные успешно импортированы: {len(records)} записей"
                        }
                        print(f"✅ EPSS загружен: {len(records)} записей")
                    else:
                        print(f"⚠️ EPSS: нет записей для загрузки")
                        results["epss"] = {
                            "success": False,
                            "count": 0,
                            "message": "EPSS файл не содержит валидных записей"
                        }
                
                # ExploitDB
                elif 'exploitdb' in file_path.lower() and file_path.endswith('.csv'):
                    print(f"💥 Загрузка ExploitDB: {file_path}")
                    
                    csv_content = zip_file.read(file_path).decode('utf-8-sig')
                    lines = csv_content.splitlines()
                    reader = csv.DictReader(lines, delimiter=',')
                    
                    records = []
                    for row in reader:
                        try:
                            # Проверяем наличие нужных полей
                            if 'id' in row:
                                # Полный формат ExploitDB
                                records.append({
                                    'exploit_id': int(row['id']),
                                    'file_path': row.get('file'),
                                    'description': row.get('description'),
                                    'date_published': parse_date(row.get('date_published')),
                                    'author': row.get('author'),
                                    'type': row.get('type'),
                                    'platform': row.get('platform'),
                                    'port': row.get('port') if row.get('port') else None,
                                    'date_added': parse_date(row.get('date_added')),
                                    'date_updated': parse_date(row.get('date_updated')),
                                    'verified': row.get('verified', '0') == '1',
                                    'codes': row.get('codes'),
                                    'tags': row.get('tags'),
                                    'aliases': row.get('aliases'),
                                    'screenshot_url': row.get('screenshot_url'),
                                    'application_url': row.get('application_url'),
                                    'source_url': row.get('source_url')
                                })
                            elif 'cve' in row and 'exploit_id' in row:
                                # Упрощенный формат (только CVE и ID)
                                cve = row.get('cve', '').strip()
                                exploit_id = row.get('exploit_id', '').strip()
                                
                                if cve and exploit_id:
                                    try:
                                        exploit_id_value = int(exploit_id)
                                        records.append({
                                            'cve': cve,
                                            'exploit_id': exploit_id_value
                                        })
                                    except ValueError:
                                        continue
                        except (ValueError, KeyError):
                            continue
                    
                    # Сохраняем в базу
                    await db.insert_exploitdb_records(records)
                    results["exploitdb"] = {
                        "success": True,
                        "count": len(records),
                        "message": f"ExploitDB данные успешно импортированы: {len(records)} записей"
                    }
                    print(f"✅ ExploitDB загружен: {len(records)} записей")
                
                # Metasploit
                elif 'metasploit' in file_path.lower() and file_path.endswith('.json'):
                    print(f"🎯 Загрузка Metasploit: {file_path}")
                    
                    json_content = zip_file.read(file_path).decode('utf-8')
                    data = json.loads(json_content)
                    
                    # Используем существующий сервис для обработки
                    count = await metasploit_service.process_and_save_metasploit_data(data)
                    
                    results["metasploit"] = {
                        "success": True,
                        "count": count,
                        "message": f"Metasploit данные успешно импортированы: {count} модулей"
                    }
                    print(f"✅ Metasploit загружен: {count} модулей")
                
                # CVE
                elif 'cve' in file_path.lower() and file_path.endswith('.json.gz'):
                    print(f"🔐 Загрузка CVE: {file_path}")
                    
                    # Распаковываем gzip
                    gz_content = zip_file.read(file_path)
                    with gzip.GzipFile(fileobj=io.BytesIO(gz_content)) as gz:
                        json_content = gz.read().decode('utf-8')
                    
                    # Парсим JSON
                    records = parse_cve_json(json_content)
                    
                    if records:
                        # Сохраняем в базу
                        await db.insert_cve_records(records)
                        
                        # Обновляем счетчик
                        current_count = results["cve"].get("count", 0)
                        results["cve"] = {
                            "success": True,
                            "count": current_count + len(records),
                            "message": f"CVE данные успешно импортированы"
                        }
                        print(f"✅ CVE файл загружен: {len(records)} записей")
                
            except Exception as file_error:
                print(f"❌ Ошибка обработки файла {file_path}: {file_error}")
                print(traceback.format_exc())
                continue
        
        # Формируем итоговый отчет
        total_count = sum(r["count"] for r in results.values())
        success_count = sum(1 for r in results.values() if r["success"])
        
        # Обновляем сообщения для CVE
        if results["cve"]["success"]:
            results["cve"]["message"] = f"CVE данные успешно импортированы: {results['cve']['count']} записей"
        
        return {
            "success": True,
            "total_records": total_count,
            "databases_imported": success_count,
            "details": results,
            "message": f"Импортировано {success_count} баз данных, всего {total_count} записей"
        }
        
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Некорректный ZIP архив")
    except Exception as e:
        print(f'❌ Archive upload error: {traceback.format_exc()}')
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/archive/status")
async def archive_status():
    """Получить статус всех баз данных"""
    try:
        db = get_db()
        
        epss_count = await db.count_epss_records()
        exploitdb_count = await db.count_exploitdb_records()
        cve_count = await db.count_cve_records()
        metasploit_count = await db.count_metasploit_modules()
        
        return {
            "success": True,
            "databases": {
                "epss": epss_count,
                "exploitdb": exploitdb_count,
                "cve": cve_count,
                "metasploit": metasploit_count
            },
            "total": epss_count + exploitdb_count + cve_count + metasploit_count
        }
    except Exception as e:
        print('Archive status error:', traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

