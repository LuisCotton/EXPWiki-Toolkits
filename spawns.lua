local p = {}

local dataCache

local function loadData()
    if dataCache then
        return dataCache
    end
    local ok, data = pcall(mw.loadJsonData, 'Spawns.json')
    if not ok or type(data) ~= 'table' then
        local title = mw.title.new('Spawns.json')
        if not title or not title.exists then
            return nil
        end
        ok, data = pcall(mw.text.jsonDecode, title:getContent() or '')
        if not ok or type(data) ~= 'table' then
            return nil
        end
    end
    dataCache = data.entries or data
    return dataCache
end

local function valueOrDefault(value, default)
    if value == nil or value == '' then
        return default
    end
    return value
end

local function terrainText(terrain)
    local result = {'陆路'}
    if type(terrain) == 'table' then
        if terrain.water then
            table.insert(result, '水路')
        end
        if terrain.air then
            table.insert(result, '空路')
        end
        if terrain.excludedTags then
            if terrain.excludedTags == 'day' then
                table.insert(result, '白天不生成')
            else
                table.insert(result, '排除标签：' .. terrain.excludedTags)
            end
        end
    end
    return table.concat(result, '、')
end

local function weightText(weight)
    if type(weight) ~= 'table' then
        return ''
    end
    local text = tostring(valueOrDefault(weight.base, ''))
    if weight.decreaseStart ~= nil or weight.decreaseEnd ~= nil or weight.decreasePerFlag ~= nil then
        text = text .. string.format(
            '，于第%s面旗帜开始降低，于第%s面旗帜停止降低，每面旗帜降低%s',
            valueOrDefault(weight.decreaseStart, '?'),
            valueOrDefault(weight.decreaseEnd, '?'),
            valueOrDefault(weight.decreasePerFlag, '?')
        )
    end
    return text
end

local function matchMonster(entry, key)
    return entry.name == key or entry.id == key or entry.entity == key
end

local function tableFor(entry)
    local preview = type(entry.preview) == 'table' and entry.preview or {}
    return '{| class="wikitable"\n'
        .. '! 生成点数(spawn level)\n'
        .. '| ' .. valueOrDefault(entry.level, '') .. '\n'
        .. '|-\n'
        .. '! 最小生成波数(spawn minWave)\n'
        .. '| ' .. valueOrDefault(entry.minWave, 1) .. '\n'
        .. '|-\n'
        .. '! 出怪预览个数(preview count)\n'
        .. '| ' .. valueOrDefault(preview.count, 1) .. '\n'
        .. '|-\n'
        .. '! 可生成区域(terrain)\n'
        .. '| ' .. terrainText(entry.terrain) .. '\n'
        .. '|-\n'
        .. '! 生成权重(weight)\n'
        .. '| ' .. weightText(entry.weight) .. '\n'
        .. '|}'
end

function p.getSpawns(frame)
    local data = loadData()
    if not data then
        return '错误：无法加载 [[Spawns.json]]'
    end

    local key = frame.args[1]
    if not key or key == '' then
        local parent = frame:getParent()
        if parent then
            key = parent:getTitle():gsub('^[^:]+:', '')
        end
    end
    if not key or key == '' then
        return '错误：请提供怪物中文名或ID。'
    end

    local tables = {}
    for _, entry in ipairs(data) do
        if matchMonster(entry, key) then
            table.insert(tables, tableFor(entry))
        end
    end

    if #tables == 0 then
        return '没有找到「' .. key .. '」对应的生成项。'
    end
    return table.concat(tables, '\n')
end

return p