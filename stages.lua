local p = {}

local dataCache

local function loadData()
    if dataCache then
        return dataCache
    end
    local ok, data = pcall(mw.loadJsonData, 'Stages.json')
    if not ok or type(data) ~= 'table' then
        local title = mw.title.new('Stages.json')
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

local function keyOf(frame)
    local key = frame.args[1]
    if not key or key == '' then
        local parent = frame:getParent()
        if parent then
            key = parent:getTitle():gsub('^[^:]+:', '')
        end
    end
    return key
end

local function matchStage(stage, key)
    return stage.displayName == key or stage.name == key or stage.id == key
end

local function spawnName(spawn)
    return spawn.name or spawn.id or ''
end

local function stageText(stage)
    local spawns = type(stage.spawns) == 'table' and stage.spawns or {}
    local links = {}
    local icons = {}
    for _, spawn in ipairs(spawns) do
        local name = spawnName(spawn)
        if name ~= '' then
            table.insert(links, '[[' .. name .. ']]')
            if not spawn.noIcon then
                table.insert(icons, '{{Spr_E|' .. name .. '}}')
            end
        end
    end

    local spawnText = #links > 0 and table.concat(links, '、') or '无'
    local result = {
        '===自然生成===',
        '默认出怪表：' .. spawnText,
    }
    if #icons > 0 then
        table.insert(result, '')
        for _, icon in ipairs(icons) do
            table.insert(result, icon)
        end
    end
    return table.concat(result, '\n')
end

function p.getStages(frame)
    local data = loadData()
    if not data then
        return '错误：无法加载 [[Stages.json]]'
    end

    local key = keyOf(frame)
    if not key or key == '' then
        return '错误：请提供关卡名或ID。'
    end

    for _, stage in ipairs(data) do
        if matchStage(stage, key) then
            return frame:preprocess(stageText(stage))
        end
    end
    return '没有找到「' .. key .. '」对应的关卡。'
end

p.getStage = p.getStages

return p