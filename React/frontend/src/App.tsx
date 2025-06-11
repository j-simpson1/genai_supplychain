import { useState } from 'react'

function VehicleForm() {
  const [formData, setFormData] = useState({
    vehicle: '',
    model: '',
    type: ''
  })

  const vehicleBrands = [
    'Toyota', 'Honda', 'Ford', 'Chevrolet', 'BMW', 'Mercedes-Benz', 'Audi',
    'Volkswagen', 'Nissan', 'Hyundai', 'Kia', 'Mazda', 'Subaru', 'Lexus',
    'Acura', 'Infiniti', 'Cadillac', 'Lincoln', 'Buick', 'GMC', 'Jeep',
    'Ram', 'Dodge', 'Chrysler', 'Volvo', 'Jaguar', 'Land Rover', 'Porsche',
    'Tesla', 'Genesis', 'Alfa Romeo', 'Maserati', 'Ferrari', 'Lamborghini'
  ]

  const modelsByBrand = {
    'Toyota': ['Camry', 'Corolla', 'RAV4', 'Highlander', 'Prius', 'Tacoma', 'Tundra', '4Runner', 'Sienna', 'Avalon'],
    'Honda': ['Civic', 'Accord', 'CR-V', 'Pilot', 'HR-V', 'Passport', 'Ridgeline', 'Insight', 'Odyssey', 'Fit'],
    'Ford': ['F-150', 'Mustang', 'Explorer', 'Escape', 'Edge', 'Expedition', 'Ranger', 'Bronco', 'Focus', 'Fusion'],
    'Chevrolet': ['Silverado', 'Equinox', 'Malibu', 'Traverse', 'Tahoe', 'Suburban', 'Colorado', 'Camaro', 'Corvette', 'Cruze'],
    'BMW': ['3 Series', '5 Series', '7 Series', 'X1', 'X3', 'X5', 'X7', 'i3', 'i8', 'Z4'],
    'Mercedes-Benz': ['C-Class', 'E-Class', 'S-Class', 'GLA', 'GLC', 'GLE', 'GLS', 'A-Class', 'CLA', 'SL'],
    'Audi': ['A3', 'A4', 'A6', 'A8', 'Q3', 'Q5', 'Q7', 'Q8', 'TT', 'R8'],
    'Tesla': ['Model 3', 'Model Y', 'Model S', 'Model X', 'Cybertruck']
  }

  const availableModels = formData.vehicle ? (modelsByBrand[formData.vehicle] || []) : []

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value,
      // Reset model when vehicle brand changes
      ...(name === 'vehicle' && { model: '' })
    }))
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    console.log('Form submitted:', formData)
    alert(`Vehicle: ${formData.vehicle}, Model: ${formData.model}, Type: ${formData.type}`)
  }

  const handleReset = () => {
    setFormData({
      vehicle: '',
      model: '',
      type: ''
    })
  }

  const selectStyle = {
    width: '100%',
    padding: '14px 16px',
    border: '2px solid #e5e7eb',
    borderRadius: '12px',
    fontSize: '16px',
    fontFamily: 'inherit',
    outline: 'none',
    transition: 'all 0.2s ease',
    backgroundColor: '#ffffff',
    cursor: 'pointer',
    boxSizing: 'border-box'
  }

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: '#f8fafc',
      padding: '20px',
      overflow: 'auto',
      zIndex: 1000
    }}>
      <div style={{
        maxWidth: '450px',
        margin: '40px auto',
        backgroundColor: 'white',
        borderRadius: '16px',
        boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
        padding: '40px',
        fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
      }}>
        <h2 style={{
          fontSize: '28px',
          fontWeight: '700',
          color: '#1f2937',
          textAlign: 'center',
          marginTop: '0',
          marginBottom: '32px',
          letterSpacing: '-0.025em'
        }}>
          Vehicle Information
        </h2>

        <div style={{ marginBottom: '24px' }}>
          <label style={{
            display: 'block',
            fontSize: '15px',
            fontWeight: '600',
            color: '#374151',
            marginBottom: '8px'
          }}>
            Vehicle Brand
          </label>
          <select
            name="vehicle"
            value={formData.vehicle}
            onChange={handleInputChange}
            required
            style={selectStyle}
            onFocus={(e) => {
              e.target.style.borderColor = '#3b82f6'
              e.target.style.boxShadow = '0 0 0 4px rgba(59, 130, 246, 0.1)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#e5e7eb'
              e.target.style.boxShadow = 'none'
            }}
          >
            <option value="">Choose a vehicle brand</option>
            {vehicleBrands.map(brand => (
              <option key={brand} value={brand}>{brand}</option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: '24px' }}>
          <label style={{
            display: 'block',
            fontSize: '15px',
            fontWeight: '600',
            color: '#374151',
            marginBottom: '8px'
          }}>
            Model
          </label>
          <select
            name="model"
            value={formData.model}
            onChange={handleInputChange}
            required
            disabled={!formData.vehicle}
            style={{
              ...selectStyle,
              opacity: !formData.vehicle ? 0.5 : 1,
              cursor: !formData.vehicle ? 'not-allowed' : 'pointer'
            }}
            onFocus={(e) => {
              if (formData.vehicle) {
                e.target.style.borderColor = '#3b82f6'
                e.target.style.boxShadow = '0 0 0 4px rgba(59, 130, 246, 0.1)'
              }
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#e5e7eb'
              e.target.style.boxShadow = 'none'
            }}
          >
            <option value="">
              {!formData.vehicle ? 'Select a brand first' : 'Choose a model'}
            </option>
            {availableModels.map(model => (
              <option key={model} value={model}>{model}</option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: '32px' }}>
          <label style={{
            display: 'block',
            fontSize: '15px',
            fontWeight: '600',
            color: '#374151',
            marginBottom: '8px'
          }}>
            Vehicle Type
          </label>
          <select
            name="type"
            value={formData.type}
            onChange={handleInputChange}
            required
            style={selectStyle}
            onFocus={(e) => {
              e.target.style.borderColor = '#3b82f6'
              e.target.style.boxShadow = '0 0 0 4px rgba(59, 130, 246, 0.1)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#e5e7eb'
              e.target.style.boxShadow = 'none'
            }}
          >
            <option value="">Choose a vehicle type</option>
            <option value="sedan">🚙 Sedan</option>
            <option value="suv">🚗 SUV</option>
            <option value="hatchback">🚘 Hatchback</option>
            <option value="coupe">🏎️ Coupe</option>
            <option value="convertible">🏎️ Convertible</option>
            <option value="pickup">🛻 Pickup Truck</option>
            <option value="van">🚐 Van</option>
            <option value="motorcycle">🏍️ Motorcycle</option>
          </select>
        </div>

        <div style={{
          display: 'flex',
          gap: '16px',
          marginBottom: '32px'
        }}>
          <button
            onClick={handleSubmit}
            style={{
              flex: '1',
              padding: '16px 24px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '12px',
              fontSize: '16px',
              fontWeight: '600',
              fontFamily: 'inherit',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
            onMouseEnter={(e) => {
              e.target.style.backgroundColor = '#2563eb'
              e.target.style.transform = 'translateY(-2px)'
              e.target.style.boxShadow = '0 8px 12px -1px rgba(0, 0, 0, 0.15)'
            }}
            onMouseLeave={(e) => {
              e.target.style.backgroundColor = '#3b82f6'
              e.target.style.transform = 'translateY(0)'
              e.target.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
          >
            ✅ Submit
          </button>
        </div>

      </div>
    </div>
  )
}

export default VehicleForm