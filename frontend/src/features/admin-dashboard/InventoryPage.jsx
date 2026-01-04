import React, { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Card, Button, Modal, Input } from '../../components/ui'
import { api, formatCurrency } from '../../utils/api'

/**
 * Página de Inventário - Visualização e gerenciamento de estoque.
 */
const InventoryPage = () => {
  const [inventorySummary, setInventorySummary] = useState(null)
  const [categories, setCategories] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [isAdjustModalOpen, setIsAdjustModalOpen] = useState(false)
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [adjustForm, setAdjustForm] = useState({
    unit_type: 'UNITARIO',
    quantity: 0
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Filtros e busca
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [stockFilter, setStockFilter] = useState('all') // 'all', 'in_stock', 'out_of_stock', 'low_stock'

  useEffect(() => {
    fetchInventorySummary()
    fetchCategories()
  }, [])

  const fetchInventorySummary = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await api.get('/api/v1/admin/inventory/summary')
      setInventorySummary(response.data)
    } catch (err) {
      console.error('Erro ao carregar inventário:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar inventário')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchCategories = async () => {
    try {
      const response = await api.get('/api/v1/admin/product-categories')
      setCategories(response.data || [])
    } catch (err) {
      console.error('Erro ao carregar categorias:', err)
      // Não mostrar erro ao usuário, apenas não mostrar categorias no filtro
    }
  }

  const handleOpenAdjustModal = (product) => {
    setSelectedProduct(product)
    setAdjustForm({
      unit_type: 'UNITARIO',
      quantity: 0
    })
    setIsAdjustModalOpen(true)
  }

  const handleCloseAdjustModal = () => {
    setIsAdjustModalOpen(false)
    setSelectedProduct(null)
    setAdjustForm({
      unit_type: 'UNITARIO',
      quantity: 0
    })
  }

  const handleAdjustStock = async (e) => {
    e.preventDefault()
    
    if (!selectedProduct || adjustForm.quantity === 0) {
      setError('Informe uma quantidade válida')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)

      // Buscar entradas existentes do produto
      const entriesResponse = await api.get(
        `/api/v1/admin/inventory/stock-entries?product_id=${selectedProduct.product_id}`
      )
      const existingEntries = entriesResponse.data || []

      // Verificar se já existe entrada com o mesmo unit_type
      const existingEntry = existingEntries.find(
        entry => entry.unit_type === adjustForm.unit_type
      )

      if (existingEntry) {
        // Atualizar entrada existente
        const newQuantity = existingEntry.quantity + adjustForm.quantity
        if (newQuantity < 0) {
          setError('Quantidade não pode ser negativa')
          return
        }
        await api.put(`/api/v1/admin/inventory/stock-entries/${existingEntry.id}`, {
          quantity: newQuantity
        })
      } else {
        // Criar nova entrada
        if (adjustForm.quantity < 0) {
          setError('Não é possível criar entrada com quantidade negativa')
          return
        }
        await api.post('/api/v1/admin/inventory/stock-entries', {
          product_id: selectedProduct.product_id,
          unit_type: adjustForm.unit_type,
          quantity: adjustForm.quantity
        })
      }

      // Recarregar resumo
      await fetchInventorySummary()
      handleCloseAdjustModal()
    } catch (err) {
      console.error('Erro ao ajustar estoque:', err)
      setError(err.response?.data?.detail || 'Erro ao ajustar estoque')
    } finally {
      setIsSubmitting(false)
    }
  }

  const getUnitTypeLabel = (type) => {
    const labels = {
      'UNITARIO': 'Unitário',
      'PACOTE': 'Pacote',
      'CAIXA': 'Caixa'
    }
    return labels[type] || type
  }

  // Filtrar itens com base nos filtros e busca
  const filteredItems = useMemo(() => {
    if (!inventorySummary || !inventorySummary.items) return []

    let items = [...inventorySummary.items]

    // Filtro de busca (nome do produto ou categoria)
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim()
      items = items.filter(item => 
        item.product_name.toLowerCase().includes(query) ||
        (item.category_name && item.category_name.toLowerCase().includes(query))
      )
    }

    // Filtro por categoria
    if (categoryFilter) {
      items = items.filter(item => 
        item.category_name === categoryFilter
      )
    }

    // Filtro por status de estoque
    if (stockFilter === 'in_stock') {
      items = items.filter(item => item.total_quantity > 0)
    } else if (stockFilter === 'out_of_stock') {
      items = items.filter(item => item.total_quantity === 0)
    } else if (stockFilter === 'low_stock') {
      items = items.filter(item => item.total_quantity > 0 && item.total_quantity < 10)
    }

    return items
  }, [inventorySummary, searchQuery, categoryFilter, stockFilter])

  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text">Inventário</h1>
          <p className="text-gray-600 mt-1">
            Controle de produtos, estoque e custos internos
          </p>
        </div>
        <Link to="/admin/produtos">
          <Button variant="primary">
            Gerenciar Produtos
          </Button>
        </Link>
      </div>

      {/* Mensagem de erro */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Filtros e Busca */}
      {inventorySummary && inventorySummary.items.length > 0 && (
        <Card className="p-4">
          <div className="space-y-4">
            {/* Campo de Busca */}
            <div>
              <label className="block text-sm font-semibold text-text mb-2">
                Buscar Produto ou Categoria
              </label>
              <Input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Digite o nome do produto ou categoria..."
                className="w-full"
              />
            </div>

            {/* Filtros */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Filtro por Categoria */}
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Filtrar por Categoria
                </label>
                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="">Todas as categorias</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.name}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Filtro por Status de Estoque */}
              <div>
                <label className="block text-sm font-semibold text-text mb-2">
                  Filtrar por Estoque
                </label>
                <select
                  value={stockFilter}
                  onChange={(e) => setStockFilter(e.target.value)}
                  className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
                >
                  <option value="all">Todos</option>
                  <option value="in_stock">Com Estoque</option>
                  <option value="out_of_stock">Sem Estoque</option>
                  <option value="low_stock">Estoque Baixo (&lt; 10)</option>
                </select>
              </div>
            </div>

            {/* Botão de Limpar Filtros */}
            {(searchQuery || categoryFilter || stockFilter !== 'all') && (
              <div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setSearchQuery('')
                    setCategoryFilter('')
                    setStockFilter('all')
                  }}
                >
                  Limpar Filtros
                </Button>
              </div>
            )}

            {/* Resultado da busca */}
            {filteredItems.length !== inventorySummary.items.length && (
              <div className="text-sm text-gray-600">
                Mostrando {filteredItems.length} de {inventorySummary.items.length} produtos
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Resumo Geral */}
      {inventorySummary && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="p-4">
            <p className="text-sm text-gray-600 mb-1">Total de Produtos</p>
            <p className="text-2xl font-bold text-text">
              {inventorySummary.total_products}
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-sm text-gray-600 mb-1">Valor Total do Estoque</p>
            <p className="text-2xl font-bold text-primary">
              {formatCurrency(parseFloat(inventorySummary.total_value))}
            </p>
          </Card>
          <Card className="p-4">
            <p className="text-sm text-gray-600 mb-1">Itens com Estoque</p>
            <p className="text-2xl font-bold text-text">
              {inventorySummary.items.filter(item => item.total_quantity > 0).length}
            </p>
          </Card>
        </div>
      )}

      {/* Lista de Produtos */}
      {isLoading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        </div>
      ) : inventorySummary && inventorySummary.items.length > 0 ? (
        <>
          {filteredItems.length > 0 ? (
            <Card>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse">
                  <thead>
                    <tr className="bg-gray-100">
                      <th className="border border-gray-300 px-4 py-3 text-left text-sm font-semibold">
                        Produto
                      </th>
                      <th className="border border-gray-300 px-4 py-3 text-left text-sm font-semibold">
                        Categoria
                      </th>
                      <th className="border border-gray-300 px-4 py-3 text-left text-sm font-semibold">
                        Custo Unitário
                      </th>
                      <th className="border border-gray-300 px-4 py-3 text-left text-sm font-semibold">
                        Quantidade
                      </th>
                      <th className="border border-gray-300 px-4 py-3 text-left text-sm font-semibold">
                        Valor Total
                      </th>
                      <th className="border border-gray-300 px-4 py-3 text-center text-sm font-semibold">
                        Ações
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredItems.map((item) => (
                      <tr key={item.product_id} className="hover:bg-gray-50">
                    <td className="border border-gray-300 px-4 py-3 text-sm font-semibold">
                      {item.product_name}
                    </td>
                    <td className="border border-gray-300 px-4 py-3 text-sm text-gray-600">
                      {item.category_name || '-'}
                    </td>
                    <td className="border border-gray-300 px-4 py-3 text-sm">
                      {formatCurrency(parseFloat(item.unit_cost))}
                    </td>
                    <td className="border border-gray-300 px-4 py-3 text-sm">
                      <span className={`font-semibold ${item.total_quantity > 0 ? 'text-green-600' : 'text-gray-400'}`}>
                        {item.total_quantity} un.
                      </span>
                    </td>
                    <td className="border border-gray-300 px-4 py-3 text-sm font-semibold text-primary">
                      {formatCurrency(parseFloat(item.total_value))}
                    </td>
                    <td className="border border-gray-300 px-4 py-3 text-center">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleOpenAdjustModal(item)}
                      >
                        Ajustar Estoque
                      </Button>
                    </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          ) : (
            <Card>
              <div className="text-center py-12">
                <div className="text-6xl mb-4">🔍</div>
                <h3 className="text-lg font-semibold text-text mb-2">
                  Nenhum produto encontrado
                </h3>
                <p className="text-gray-600 mb-6">
                  Tente ajustar os filtros de busca
                </p>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setSearchQuery('')
                    setCategoryFilter('')
                    setStockFilter('all')
                  }}
                >
                  Limpar Filtros
                </Button>
              </div>
            </Card>
          )}
        </>
      ) : (
        <Card>
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📦</div>
            <h3 className="text-lg font-semibold text-text mb-2">
              Nenhum produto cadastrado
            </h3>
            <p className="text-gray-600 mb-6">
              Comece cadastrando produtos para gerenciar seu inventário
            </p>
            <Link to="/admin/produtos">
              <Button variant="primary">
                Cadastrar Primeiro Produto
              </Button>
            </Link>
          </div>
        </Card>
      )}

      {/* Modal de Ajuste de Estoque */}
      <Modal
        isOpen={isAdjustModalOpen}
        onClose={handleCloseAdjustModal}
        title={`Ajustar Estoque - ${selectedProduct?.product_name || ''}`}
      >
        <form onSubmit={handleAdjustStock} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Tipo de Unidade
            </label>
            <select
              value={adjustForm.unit_type}
              onChange={(e) => setAdjustForm({ ...adjustForm, unit_type: e.target.value })}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isSubmitting}
            >
              <option value="UNITARIO">Unitário</option>
              <option value="PACOTE">Pacote</option>
              <option value="CAIXA">Caixa</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Quantidade (use negativo para remover)
            </label>
            <Input
              type="number"
              value={adjustForm.quantity}
              onChange={(e) => setAdjustForm({ ...adjustForm, quantity: parseInt(e.target.value) || 0 })}
              placeholder="Ex: 10 para adicionar, -5 para remover"
              required
              disabled={isSubmitting}
            />
            <p className="text-xs text-gray-500 mt-1">
              Quantidade atual: {selectedProduct?.total_quantity || 0} unidades
            </p>
          </div>

          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={handleCloseAdjustModal}
              disabled={isSubmitting}
              className="flex-1"
            >
              Cancelar
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting}
              className="flex-1"
            >
              {isSubmitting ? 'Salvando...' : 'Ajustar Estoque'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

export default InventoryPage

