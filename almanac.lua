local p = {}
local cache

local function loadData()
    if cache then
        return cache
    end
    local title = mw.title.new('Almanac.json')
    if not title or not title.exists then
        return nil
    end
    local ok, decoded = pcall(mw.text.jsonDecode, title:getContent() or '')
    if not ok or type(decoded) ~= 'table' then
        return nil
    end
    cache = {}
    for _, item in ipairs(decoded) do
        if item.id then
            cache[item.id] = item
            cache[item.id:lower()] = item
        end
        if item.name then cache[item.name] = item end
    end
    return cache
end

local function format(text)
    if type(text) ~= 'string' then
        return ''
    end
    return text:gsub('<color=([^>]+)>', '<span style="color:%1">'):gsub('</color>', '</span>')
end

local function join(value, separator, suffix)
    if type(value) == 'table' then
        local result = {}
        for _, text in ipairs(value) do
            if text ~= '' then table.insert(result, format(text) .. (suffix or '')) end
        end
        return table.concat(result, separator or '')
    end
    if value and value ~= '' then return format(value) .. (suffix or '') end
    return ''
end

local function flavor(value)
    local text = join(value, '<br>')
    if text == '' then
        return ''
    end
    return '<poem>' .. text .. '</poem>'
end

local function isMutantEnemy(item)
    if item.type ~= 'enemy' then return false end
    if item.id == 'MutantVillager'
        or item.id == 'MegaMutantVillager'
        or item.id == 'MutantMannequin'
        or item.id == 'RandomMutant' then
        return true
    end
    for _, tag in ipairs(item.tags or {}) do
        if tag[1] == 'category' and (tag[2] == 'Mutant_Exp' or tag[2] == '突变类') then
            return true
        end
    end
    return false
end

local function icon(item, page)
    local template = item.type == 'enemy' and 'Spr_E' or 'Spr_C'
    return '{{' .. template .. '|' .. (item.name or page or '') .. '|text=1}}'
end

local function params(item, page)
    local result = {
        ' | name = ' .. (item.name or page or ''),
        ' | icon = ' .. icon(item, page),
    }
    if isMutantEnemy(item) then
        table.insert(result, ' | image size = 125')
    end
    table.insert(result, ' | desc = ' .. join(item.header, '<br>'))
    table.insert(result, ' | properties = ' .. join(item.properties, '', '<br>'))
    table.insert(result, ' | flavor = ' .. flavor(item.flavor))
    if item.cost and item.cost ~= '' then
        table.insert(result, ' | cost = ' .. item.cost)
    end
    if item.recharge and item.recharge ~= '' then
        table.insert(result, ' | recharge = ' .. item.recharge)
    end
    for index, tag in ipairs(item.tags or {}) do
        if index > 15 then break end
        table.insert(result, string.format(
            ' | tag%d = {{Tag|%s|%s|text=no}}', index, tag[1] or '', tag[2] or ''
        ))
    end
    table.insert(result, ' | new = yes')
    return table.concat(result, '\n')
end

function p.getAlmanac(frame)
    local data = loadData()
    if not data then
        return '错误：无法加载 [[Almanac.json]]'
    end
    local key = frame.args[1]
    if not key or key == '' then
        local parent = frame:getParent()
        if parent then
            key = parent:getTitle():gsub('^[^:]+:', '')
        end
    end
    if not key or key == '' then
        return '错误：请提供图鉴条目名或ID。'
    end
    local item = data[key] or data[key:lower()]
    if not item then
        return '错误：在 [[Almanac.json]] 中未找到「' .. key .. '」的数据'
    end
    return frame:preprocess('{{Almanac\n' .. params(item, key) .. '\n}}')
end

return p