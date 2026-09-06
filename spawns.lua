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

local function trim(value)
    return mw.text.trim(tostring(value or ''))
end

local function link(name)
    return '[[' .. name .. ']]'
end

local function monsterLink(entry)
    if entry.id == 'undead_flying_object_blitz' then
        return '[[飞碟闪电战|不死飞行物（飞碟闪电战）]]'
    end
    return link(entry.name or entry.id or '')
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
    end
    return table.concat(result, '、')
end

local function restrictionText(entry)
    local result = {}
    if type(entry.terrain) == 'table' and entry.terrain.excludedTags == 'day' then
        table.insert(result, '白天不生成')
    end
    if entry.noEndless then
        table.insert(result, '无尽模式不生成')
    end
    if #result == 0 then
        return '无'
    end
    return table.concat(result, '、')
end

local function weightText(weight)
    if type(weight) ~= 'table' or weight.base == nil then
        return '/'
    end
    local text = tostring(valueOrDefault(weight.base, ''))
    if weight.decreaseStart ~= nil or weight.decreaseEnd ~= nil or weight.decreasePerFlag ~= nil then
        text = text .. string.format(
            '，第%s面旗到第%s面旗期间每旗降低%s',
            valueOrDefault(weight.decreaseStart, '?'),
            valueOrDefault(weight.decreaseEnd, '?'),
            valueOrDefault(weight.decreasePerFlag, '?')
        )
    end
    return text
end

local function previewText(preview)
    if type(preview) == 'table' and preview.variant ~= nil then
        return tostring(preview.variant) .. '（变体）'
    end
    if type(preview) == 'table' then
        return tostring(valueOrDefault(preview.count, 1))
    end
    return '1'
end

local function bigRow(entry)
    return '|-\n'
        .. '| ' .. monsterLink(entry) .. ' || '
        .. tostring(valueOrDefault(entry.level, '')) .. ' || '
        .. tostring(valueOrDefault(entry.minWave, 1)) .. ' || '
        .. weightText(entry.weight) .. ' || '
        .. terrainText(entry.terrain) .. ' || '
        .. previewText(entry.preview) .. ' || '
        .. restrictionText(entry)
end

local noteFields = {
    ['占用点数'] = 'level',
    ['出怪生成波数'] = 'minWave',
    ['出怪预览个数'] = 'preview',
    ['可生成区域'] = 'terrain',
    ['生成权重'] = 'weight',
    ['其他生成限制'] = 'restrictions',
}

local function mergedArgs(frame)
    local args = {}
    local parent = frame:getParent()
    if parent then
        for key, value in pairs(parent.args) do args[key] = value end
    end
    for key, value in pairs(frame.args) do args[key] = value end
    return args, parent
end

local function addNote(notes, field, value)
    value = trim(value)
    if field and value ~= '' then table.insert(notes[field], value) end
end

local function collectNotes(args)
    local notes = {level = {}, minWave = {}, preview = {}, terrain = {}, weight = {}, restrictions = {}}
    for label, field in pairs(noteFields) do
        local ordered = {}
        for key, value in pairs(args) do
            if type(key) == 'string' then
                local suffix = key:match('^' .. label .. '(%d*)$')
                if suffix ~= nil and trim(value) ~= '' then
                    table.insert(ordered, {
                        index = suffix == '' and 1 or tonumber(suffix),
                        value = value,
                    })
                end
            end
        end
        table.sort(ordered, function(a, b) return a.index < b.index end)
        for _, item in ipairs(ordered) do addNote(notes, field, item.value) end
    end
    return notes
end

local function withNotes(frame, value, notes)
    local result = tostring(valueOrDefault(value, ''))
    for _, note in ipairs(notes) do
        result = result .. frame:extensionTag('ref', note)
    end
    return result
end

local function matchMonster(entry, key)
    return entry.name == key or entry.id == key or entry.entity == key
end

local function smallTable(frame, entry, notes)
    return '{| class="wikitable"\n'
        .. '! 占用点数\n| ' .. withNotes(frame, entry.level, notes.level) .. '\n|-\n'
        .. '! 出怪生成波数\n| ' .. withNotes(frame, valueOrDefault(entry.minWave, 1), notes.minWave) .. '\n|-\n'
        .. '! 出怪预览个数\n| ' .. withNotes(frame, previewText(entry.preview), notes.preview) .. '\n|-\n'
        .. '! 可生成区域\n| ' .. withNotes(frame, terrainText(entry.terrain), notes.terrain) .. '\n|-\n'
        .. '! 生成权重\n| ' .. withNotes(frame, weightText(entry.weight), notes.weight) .. '\n|-\n'
        .. '! 其他生成限制\n| ' .. withNotes(frame, restrictionText(entry), notes.restrictions) .. '\n|}'
end

local function bigTable(data)
    local result = {
        '{| class="wikitable"', '|-',
        '! 怪物名称 !! 占用点数 !! 出怪生成波数 !! 生成权重 !! 可生成区域 !! 出怪预览个数 !! 其他生成限制',
    }
    for _, entry in ipairs(data) do table.insert(result, bigRow(entry)) end
    table.insert(result, '|}')
    return table.concat(result, '\n')
end

function p.getSpawns(frame)
    local data = loadData()
    if not data then
        return '错误：无法加载 [[Spawns.json]]'
    end

    local args, parent = mergedArgs(frame)
    local key = trim(args[1])
    if key == '' and parent then
        key = trim(parent:getTitle():gsub('^[^:]+:', ''))
    end
    if key == '' then
        return '错误：请提供怪物中文名、ID或“怪物/生成”。'
    end
    if key == '怪物/生成' then return bigTable(data) end

    local notes = collectNotes(args)
    local result = {}
    for _, entry in ipairs(data) do
        if matchMonster(entry, key) then table.insert(result, smallTable(frame, entry, notes)) end
    end
    if #result == 0 then return '没有找到「' .. key .. '」对应的生成项。' end
    return table.concat(result, '\n')
end

return p