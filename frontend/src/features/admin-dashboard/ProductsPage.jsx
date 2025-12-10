import React, { useState, useEffect } from 'react'
import { Card, Button, Modal, Input } from '../../components/ui'
import { api, formatCurrency } from '../../utils/api'

/**
 * Página de Gerenciamento de Produtos e Categorias.
 */
const ProductsPage = () => {
  const [products, setProducts] = useState([])
  const [categories, setCategories] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  
  // Modais de Produto
  const [isProductModalOpen, setIsProductModalOpen] = useState(false)
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false)
  const [selectedProduct, setSelectedProduct] = useState(null)
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  // Formulários
  const [productForm, setProductForm] = useState({
    name: '',
    category_id: '',
    unit_cost: ''
  })
  const [categoryForm, setCategoryForm] = useState({
    name: ''
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const [productsRes, categoriesRes] = await Promise.all([
        api.get('/api/v1/admin/products'),
        api.get('/api/v1/admin/product-categories')
      ])
      setProducts(productsRes.data || [])
      setCategories(categoriesRes.data || [])
    } catch (err) {
      console.error('Erro ao carregar dados:', err)
      setError(err.response?.data?.detail || 'Erro ao carregar dados')
    } finally {
      setIsLoading(false)
    }
  }

  // Handlers de Categoria
  const handleOpenCategoryModal = (category = null) => {
    setSelectedCategory(category)
    setCategoryForm({
      name: category?.name || ''
    })
    setIsCategoryModalOpen(true)
  }

  const handleCloseCategoryModal = () => {
    setIsCategoryModalOpen(false)
    setSelectedCategory(null)
    setCategoryForm({ name: '' })
  }

  const handleSubmitCategory = async (e) => {
    e.preventDefault()
    
    if (!categoryForm.name.trim()) {
      setError('Nome da categoria é obrigatório')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)

      if (selectedCategory) {
        await api.put(`/api/v1/admin/product-categories/${selectedCategory.id}`, categoryForm)
      } else {
        await api.post('/api/v1/admin/product-categories', categoryForm)
      }

      await fetchData()
      handleCloseCategoryModal()
    } catch (err) {
      console.error('Erro ao salvar categoria:', err)
      setError(err.response?.data?.detail || 'Erro ao salvar categoria')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDeleteCategory = async (categoryId) => {
    if (!window.confirm('Tem certeza que deseja deletar esta categoria?')) {
      return
    }

    try {
      await api.delete(`/api/v1/admin/product-categories/${categoryId}`)
      await fetchData()
    } catch (err) {
      console.error('Erro ao deletar categoria:', err)
      alert(err.response?.data?.detail || 'Erro ao deletar categoria')
    }
  }

  // Handlers de Produto
  const handleOpenProductModal = (product = null) => {
    setSelectedProduct(product)
    setProductForm({
      name: product?.name || '',
      category_id: product?.category_id || '',
      unit_cost: product?.unit_cost || ''
    })
    setIsProductModalOpen(true)
  }

  const handleCloseProductModal = () => {
    setIsProductModalOpen(false)
    setSelectedProduct(null)
    setProductForm({ name: '', category_id: '', unit_cost: '' })
  }

  const handleSubmitProduct = async (e) => {
    e.preventDefault()
    
    if (!productForm.name.trim()) {
      setError('Nome do produto é obrigatório')
      return
    }
    if (!productForm.unit_cost || parseFloat(productForm.unit_cost) < 0) {
      setError('Custo unitário deve ser um valor válido')
      return
    }

    try {
      setIsSubmitting(true)
      setError(null)

      const payload = {
        ...productForm,
        category_id: productForm.category_id || null,
        unit_cost: parseFloat(productForm.unit_cost)
      }

      if (selectedProduct) {
        await api.put(`/api/v1/admin/products/${selectedProduct.id}`, payload)
      } else {
        await api.post('/api/v1/admin/products', payload)
      }

      await fetchData()
      handleCloseProductModal()
    } catch (err) {
      console.error('Erro ao salvar produto:', err)
      setError(err.response?.data?.detail || 'Erro ao salvar produto')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDeleteProduct = async (productId) => {
    if (!window.confirm('Tem certeza que deseja deletar este produto?')) {
      return
    }

    try {
      await api.delete(`/api/v1/admin/products/${productId}`)
      await fetchData()
    } catch (err) {
      console.error('Erro ao deletar produto:', err)
      alert(err.response?.data?.detail || 'Erro ao deletar produto')
    }
  }

  const getCategoryName = (categoryId) => {
    if (!categoryId) return '-'
    const category = categories.find(c => c.id === categoryId)
    return category?.name || '-'
  }

  return (
    <div className="space-y-6">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text">Produtos e Categorias</h1>
          <p className="text-gray-600 mt-1">
            Gerencie seus produtos e categorias do inventário
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => handleOpenCategoryModal()}>
            Nova Categoria
          </Button>
          <Button variant="primary" onClick={() => handleOpenProductModal()}>
            Novo Produto
          </Button>
        </div>
      </div>

      {/* Mensagem de erro */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Lista de Categorias */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-text">Categorias</h2>
          <Button variant="secondary" size="sm" onClick={() => handleOpenCategoryModal()}>
            + Adicionar
          </Button>
        </div>
        {categories.length > 0 ? (
          <div className="space-y-2">
            {categories.map((category) => (
              <div
                key={category.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
              >
                <span className="font-medium">{category.name}</span>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleOpenCategoryModal(category)}
                  >
                    Editar
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleDeleteCategory(category.id)}
                  >
                    Deletar
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500 text-center py-4">
            Nenhuma categoria cadastrada. Clique em "Nova Categoria" para começar.
          </p>
        )}
      </Card>

      {/* Lista de Produtos */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-text">Produtos</h2>
          <Button variant="primary" size="sm" onClick={() => handleOpenProductModal()}>
            + Adicionar
          </Button>
        </div>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : products.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-gray-100">
                  <th className="border border-gray-300 px-4 py-3 text-left text-sm font-semibold">
                    Nome
                  </th>
                  <th className="border border-gray-300 px-4 py-3 text-left text-sm font-semibold">
                    Categoria
                  </th>
                  <th className="border border-gray-300 px-4 py-3 text-left text-sm font-semibold">
                    Custo Unitário
                  </th>
                  <th className="border border-gray-300 px-4 py-3 text-center text-sm font-semibold">
                    Ações
                  </th>
                </tr>
              </thead>
              <tbody>
                {products.map((product) => (
                  <tr key={product.id} className="hover:bg-gray-50">
                    <td className="border border-gray-300 px-4 py-3 text-sm font-semibold">
                      {product.name}
                    </td>
                    <td className="border border-gray-300 px-4 py-3 text-sm text-gray-600">
                      {getCategoryName(product.category_id)}
                    </td>
                    <td className="border border-gray-300 px-4 py-3 text-sm">
                      {formatCurrency(parseFloat(product.unit_cost))}
                    </td>
                    <td className="border border-gray-300 px-4 py-3 text-center">
                      <div className="flex justify-center gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleOpenProductModal(product)}
                        >
                          Editar
                        </Button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => handleDeleteProduct(product.id)}
                        >
                          Deletar
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">
            Nenhum produto cadastrado. Clique em "Novo Produto" para começar.
          </p>
        )}
      </Card>

      {/* Modal de Categoria */}
      <Modal
        isOpen={isCategoryModalOpen}
        onClose={handleCloseCategoryModal}
        title={selectedCategory ? 'Editar Categoria' : 'Nova Categoria'}
      >
        <form onSubmit={handleSubmitCategory} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <Input
            label="Nome da Categoria"
            value={categoryForm.name}
            onChange={(e) => setCategoryForm({ ...categoryForm, name: e.target.value })}
            placeholder="Ex: Materiais, Equipamentos"
            required
            disabled={isSubmitting}
          />

          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={handleCloseCategoryModal}
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
              {isSubmitting ? 'Salvando...' : 'Salvar'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Modal de Produto */}
      <Modal
        isOpen={isProductModalOpen}
        onClose={handleCloseProductModal}
        title={selectedProduct ? 'Editar Produto' : 'Novo Produto'}
      >
        <form onSubmit={handleSubmitProduct} className="space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}

          <Input
            label="Nome do Produto"
            value={productForm.name}
            onChange={(e) => setProductForm({ ...productForm, name: e.target.value })}
            placeholder="Ex: Algodão, Álcool 70%"
            required
            disabled={isSubmitting}
          />

          <div>
            <label className="block text-sm font-semibold text-text mb-2">
              Categoria (Opcional)
            </label>
            <select
              value={productForm.category_id}
              onChange={(e) => setProductForm({ ...productForm, category_id: e.target.value })}
              className="w-full px-4 py-3 rounded-lg border-2 border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary"
              disabled={isSubmitting}
            >
              <option value="">Sem categoria</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name}
                </option>
              ))}
            </select>
          </div>

          <Input
            label="Custo Unitário (R$)"
            type="number"
            step="0.01"
            min="0"
            value={productForm.unit_cost}
            onChange={(e) => setProductForm({ ...productForm, unit_cost: e.target.value })}
            placeholder="0.00"
            required
            disabled={isSubmitting}
          />

          <div className="flex gap-3 pt-4">
            <Button
              type="button"
              variant="secondary"
              onClick={handleCloseProductModal}
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
              {isSubmitting ? 'Salvando...' : 'Salvar'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}

export default ProductsPage

